"""
Node Rewards Scheduler for VictoriaMetrics
Directly interacts with IC canisters to fetch node rewards data and push to VictoriaMetrics
"""

import logging
import os
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional
from urllib.parse import urljoin

import requests
from ic.agent import Agent
from ic.candid import Types, encode
from ic.client import Client
from ic.identity import Identity

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


class ICCanisterClient:
    """Client for interacting with Internet Computer canisters"""

    # IC mainnet URL
    IC_URL = "https://ic0.app"

    # Canister IDs
    NODE_REWARDS_CANISTER_ID = (
        "uuew5-iiaaa-aaaaa-qbx4q-cai"  # Node rewards canister (DEV)
    )
    GOVERNANCE_CANISTER_ID = "rrkah-fqaaa-aaaaa-aaaaq-cai"  # NNS Governance canister

    def __init__(self):
        # Create anonymous identity
        self.identity = Identity()
        self.client = Client(url=self.IC_URL)
        self.agent = Agent(self.identity, self.client)

    def get_rewards_daily(self, date_str: str) -> Dict[str, Any]:
        """Fetch daily rewards data from node rewards canister"""

        try:
            # Parse date
            date_obj = datetime.strptime(date_str, "%Y-%m-%d")

            # Define Candid types for the argument
            # DateUtc: record { year: nat16; month: nat8; day: nat8 }
            date_utc_type = Types.Record(
                {
                    "year": Types.Nat32,
                    "month": Types.Nat32,
                    "day": Types.Nat32,
                }
            )

            # GetNodeProvidersRewardsCalculationRequest: record { day: DateUtc }
            request_type = Types.Record({"day": date_utc_type})

            # Define return type structure
            # NodeMetricsDaily
            node_metrics_daily_type = Types.Record(
                {
                    "subnet_assigned": Types.Opt(Types.Principal),
                    "subnet_assigned_failure_rate": Types.Opt(Types.Float64),
                    "num_blocks_proposed": Types.Opt(Types.Nat64),
                    "num_blocks_failed": Types.Opt(Types.Nat64),
                    "original_failure_rate": Types.Opt(Types.Float64),
                    "relative_failure_rate": Types.Opt(Types.Float64),
                }
            )

            # DailyNodeFailureRate (variant)
            daily_node_failure_rate_type = Types.Variant(
                {
                    "SubnetMember": Types.Record(
                        {
                            "node_metrics": Types.Opt(node_metrics_daily_type),
                        }
                    ),
                    "NonSubnetMember": Types.Record(
                        {
                            "extrapolated_failure_rate": Types.Opt(Types.Float64),
                        }
                    ),
                }
            )

            # DailyNodeRewards
            daily_node_rewards_type = Types.Record(
                {
                    "node_id": Types.Opt(Types.Principal),
                    "node_reward_type": Types.Opt(Types.Text),
                    "region": Types.Opt(Types.Text),
                    "dc_id": Types.Opt(Types.Text),
                    "daily_node_failure_rate": Types.Opt(daily_node_failure_rate_type),
                    "performance_multiplier": Types.Opt(Types.Float64),
                    "rewards_reduction": Types.Opt(Types.Float64),
                    "base_rewards_xdr_permyriad": Types.Opt(Types.Float64),
                    "adjusted_rewards_xdr_permyriad": Types.Opt(Types.Float64),
                }
            )

            # NodeTypeRegionBaseRewards
            node_type_region_base_rewards_type = Types.Record(
                {
                    "monthly_xdr_permyriad": Types.Opt(Types.Float64),
                    "daily_xdr_permyriad": Types.Opt(Types.Float64),
                    "node_reward_type": Types.Opt(Types.Text),
                    "region": Types.Opt(Types.Text),
                }
            )

            # Type3RegionBaseRewards
            type3_region_base_rewards_type = Types.Record(
                {
                    "region": Types.Opt(Types.Text),
                    "nodes_count": Types.Opt(Types.Nat64),
                    "avg_rewards_xdr_permyriad": Types.Opt(Types.Float64),
                    "avg_coefficient": Types.Opt(Types.Float64),
                    "daily_xdr_permyriad": Types.Opt(Types.Float64),
                }
            )

            # DailyNodeProviderRewards
            daily_node_provider_rewards_type = Types.Record(
                {
                    "total_base_rewards_xdr_permyriad": Types.Opt(Types.Nat64),
                    "total_adjusted_rewards_xdr_permyriad": Types.Opt(Types.Nat64),
                    "base_rewards": Types.Vec(node_type_region_base_rewards_type),
                    "base_rewards_type3": Types.Vec(type3_region_base_rewards_type),
                    "daily_nodes_rewards": Types.Vec(daily_node_rewards_type),
                }
            )

            # DailyResults
            daily_results_type = Types.Record(
                {
                    "subnets_failure_rate": Types.Vec(
                        Types.Tuple(Types.Principal, Types.Float64)
                    ),
                    "provider_results": Types.Vec(
                        Types.Tuple(Types.Principal, daily_node_provider_rewards_type)
                    ),
                }
            )

            # GetNodeProvidersRewardsCalculationResponse: Result<DailyResults, String>
            return_type = Types.Variant(
                {
                    "Ok": daily_results_type,
                    "Err": Types.Text,
                }
            )

            # Build the argument value
            arg_value = {
                "day": {
                    "year": date_obj.year,
                    "month": date_obj.month,
                    "day": date_obj.day,
                }
            }

            # Encode with explicit type information
            arg_bytes = encode([{"type": request_type, "value": arg_value}])

            method_name = "get_node_providers_rewards_calculation"

            # Make the query with return type
            response = self.agent.query_raw(
                self.NODE_REWARDS_CANISTER_ID, method_name, arg_bytes, return_type
            )

            # Response is a list with dict containing 'type' and 'value'
            if not response or len(response) == 0:
                logger.warning(f"Empty response for {date_str}")
                return {}

            result = response[0].get("value", {})

            # Handle Result variant (Ok/Err)
            if "Ok" in result:
                daily_results = result["Ok"]

                # Convert lists of tuples to dictionaries for easier processing
                # provider_results: [[Principal, {...}], ...] -> {Principal: {...}}
                provider_results_dict = {}
                for principal, provider_data in daily_results.get(
                    "provider_results", []
                ):
                    provider_results_dict[str(principal)] = provider_data

                # subnets_failure_rate: [[Principal, float], ...] -> {Principal: float}
                subnets_failure_rate_dict = {}
                for principal, failure_rate in daily_results.get(
                    "subnets_failure_rate", []
                ):
                    subnets_failure_rate_dict[str(principal)] = failure_rate

                result_dict = {
                    "provider_results": provider_results_dict,
                    "subnets_failure_rate": subnets_failure_rate_dict,
                }

                logger.info(
                    f"Successfully fetched rewards for {date_str} ({len(provider_results_dict)} providers)"
                )
                return result_dict

            elif "Err" in result:
                error_msg = result["Err"]
                logger.warning(f"Canister returned error for {date_str}: {error_msg}")
                return {}
            else:
                logger.warning(f"Unexpected response format for {date_str}: {result}")
                return {}

        except Exception as e:
            logger.warning(
                f"Failed to fetch rewards for {date_str}: {e}", exc_info=True
            )
            return {}

    def get_latest_governance_reward_event(self) -> Optional[float]:
        """Fetch latest governance reward event timestamp from governance canister"""

        try:
            request_type = Types.Record({"date_filter": Types.Opt(Types.Nat64)})

            # Build request with no date filter to get all rewards
            # In ic-py, optional None is represented as an empty list []
            arg_bytes = encode(
                [
                    {
                        "type": request_type,
                        "value": {
                            "date_filter": []  # Empty list = None for optional types
                        },
                    }
                ]
            )

            # Make query
            response = self.agent.query_raw(
                self.GOVERNANCE_CANISTER_ID,
                "list_node_provider_rewards",
                arg_bytes,
            )

            # Extract value from response
            if not response or len(response) == 0:
                logger.warning("Empty response from governance canister")
                return None

            result = response[0].get("value", {})
            rewards_list = result.get("rewards", [])

            # Rewards are in descending order (latest first)
            if rewards_list and len(rewards_list) > 0:
                first_reward = rewards_list[0]
                timestamp = first_reward.get("timestamp")
                if timestamp:
                    logger.info(f"Latest governance reward timestamp: {timestamp}")
                    return float(timestamp)

        except Exception as e:
            logger.warning(f"Failed to fetch governance rewards: {e}", exc_info=True)

        return None


class NodeRewardsPusher:
    """Pushes node rewards metrics to VictoriaMetrics"""

    def __init__(self, victoria_url: str):
        self.victoria_url = victoria_url
        self.ic_client = ICCanisterClient()

    @staticmethod
    def _unwrap_optional(value):
        """Unwrap Candid optional values (represented as lists)"""
        if isinstance(value, list):
            return value[0] if len(value) > 0 else None
        return value

    def wait_for_victoria_metrics(self):
        """Wait for VictoriaMetrics to be ready"""

        logger.info("Waiting for VictoriaMetrics to be ready...")

        while True:
            try:
                response = requests.get(f"{self.victoria_url}/-/ready", timeout=5)
                if response.status_code == 200:
                    logger.info("✅ VictoriaMetrics is ready")
                    return
            except requests.exceptions.RequestException:
                continue

            logger.info(f"  Waiting for VictoriaMetrics at {self.victoria_url}...")
            time.sleep(2)

    def push_metrics_for_date(self, date_str: str) -> bool:
        """
        Fetch node rewards data from IC canisters and push to VictoriaMetrics for a specific date
        Returns True if successful, False otherwise
        """

        try:
            logger.info(f"Pushing node rewards data for {date_str}")

            # Parse target date
            target_date = datetime.strptime(date_str, "%Y-%m-%d")

            # Calculate noon timestamp in milliseconds
            noon_dt = target_date.replace(hour=12, minute=0, second=0, microsecond=0)
            noon_timestamp_ms = int(
                noon_dt.replace(tzinfo=timezone.utc).timestamp() * 1000
            )

            # Fetch data from IC canister
            daily_results = self.ic_client.get_rewards_daily(date_str)

            if not daily_results:
                logger.warning(f"⚠️  No data available for {date_str}")
                return False

            # Build Prometheus metrics
            metrics_lines = []

            # Provider-level metrics
            provider_results = daily_results.get("provider_results", {})
            for provider_id, provider_rewards in provider_results.items():
                provider_id_str = str(provider_id)

                # nodes_count
                nodes_count = len(provider_rewards.get("daily_nodes_rewards", []))
                metrics_lines.append(
                    f'nodes_count{{provider_id="{provider_id_str}"}} {nodes_count} {noon_timestamp_ms}'
                )

                # base_rewards
                base_rewards = self._unwrap_optional(
                    provider_rewards.get("total_base_rewards_xdr_permyriad")
                )
                if base_rewards is not None:
                    metrics_lines.append(
                        f'total_base_rewards_xdr_permyriad{{provider_id="{provider_id_str}"}} {base_rewards} {noon_timestamp_ms}'
                    )

                # adjusted_rewards
                adjusted_rewards = self._unwrap_optional(
                    provider_rewards.get("total_adjusted_rewards_xdr_permyriad")
                )
                if adjusted_rewards is not None:
                    metrics_lines.append(
                        f'total_adjusted_rewards_xdr_permyriad{{provider_id="{provider_id_str}"}} {adjusted_rewards} {noon_timestamp_ms}'
                    )

                # Node-level metrics
                for node_result in provider_rewards.get("daily_nodes_rewards", []):
                    node_id = self._unwrap_optional(node_result.get("node_id"))
                    node_id_str = str(node_id) if node_id else ""

                    # daily_node_failure_rate is optional and contains a variant
                    failure_rate_data = self._unwrap_optional(
                        node_result.get("daily_node_failure_rate")
                    )
                    if (
                        isinstance(failure_rate_data, dict)
                        and "SubnetMember" in failure_rate_data
                    ):
                        # Extract node_metrics from SubnetMember variant
                        subnet_member = failure_rate_data["SubnetMember"]
                        node_metrics = self._unwrap_optional(
                            subnet_member.get("node_metrics")
                        )

                        if node_metrics:
                            subnet_id = self._unwrap_optional(
                                node_metrics.get("subnet_assigned")
                            )
                            subnet_id_str = str(subnet_id) if subnet_id else ""

                            # original_failure_rate
                            original_fr = self._unwrap_optional(
                                node_metrics.get("original_failure_rate")
                            )
                            if original_fr is not None:
                                metrics_lines.append(
                                    f'original_failure_rate{{provider_id="{provider_id_str}",node_id="{node_id_str}",subnet_id="{subnet_id_str}"}} {original_fr} {noon_timestamp_ms}'
                                )

                            # relative_failure_rate
                            relative_fr = self._unwrap_optional(
                                node_metrics.get("relative_failure_rate")
                            )
                            if relative_fr is not None:
                                metrics_lines.append(
                                    f'relative_failure_rate{{provider_id="{provider_id_str}",node_id="{node_id_str}",subnet_id="{subnet_id_str}"}} {relative_fr} {noon_timestamp_ms}'
                                )

            # Subnet-level metrics
            subnets_failure_rate = daily_results.get("subnets_failure_rate", {})
            for subnet_id, failure_rate in subnets_failure_rate.items():
                subnet_id_str = str(subnet_id)
                metrics_lines.append(
                    f'subnet_failure_rate{{subnet_id="{subnet_id_str}"}} {failure_rate} {noon_timestamp_ms}'
                )

            # Governance timestamp
            gov_timestamp = self.ic_client.get_latest_governance_reward_event()
            if gov_timestamp:
                metrics_lines.append(
                    f"governance_latest_reward_event_timestamp_seconds {gov_timestamp} {noon_timestamp_ms}"
                )

            # Push to VictoriaMetrics
            if metrics_lines:
                metrics_payload = "\n".join(metrics_lines) + "\n"
                import_url = urljoin(
                    self.victoria_url.rstrip("/") + "/", "api/v1/import/prometheus"
                )

                response = requests.post(
                    import_url,
                    data=metrics_payload.encode("utf-8"),
                    headers={"Content-Type": "text/plain"},
                    timeout=30,
                )

                if response.status_code in (200, 204):
                    logger.info(
                        f"✅ Successfully pushed data for {date_str} ({len(metrics_lines)} metrics)"
                    )
                    return True
                else:
                    logger.error(
                        f"❌ Failed to push to VictoriaMetrics: {response.status_code} - {response.text}"
                    )
                    return False
            else:
                logger.warning(f"No metrics to push for {date_str}")
                return False

        except Exception as e:
            logger.error(f"❌ Error processing {date_str}: {e}", exc_info=True)
            return False

    def backfill(self, days: int = 40):
        """Backfill historical data"""

        logger.info(f"Starting backfill of last {days} days...")

        for i in range(days, 0, -1):
            date_obj = datetime.now(timezone.utc) - timedelta(days=i)
            date_str = date_obj.strftime("%Y-%m-%d")

            logger.info(
                f"[{days - i + 1:2d}/{days}] Backfilling data for {date_str}..."
            )
            self.push_metrics_for_date(date_str)

        logger.info("✅ Backfill complete!")

    def wait_until_next_run(self):
        """Wait until 00:05 UTC tomorrow"""
        now = datetime.now(timezone.utc)

        # Calculate next 00:05 UTC
        next_run = now.replace(hour=0, minute=5, second=0, microsecond=0)
        if now >= next_run:
            # Already past 00:05 today, schedule for tomorrow
            next_run += timedelta(days=1)

        wait_seconds = (next_run - now).total_seconds()
        logger.info(
            f"Next run scheduled for {next_run.strftime('%Y-%m-%d %H:%M:%S')} UTC"
        )
        logger.info(
            f"Waiting {wait_seconds:.0f} seconds ({wait_seconds / 3600:.1f} hours)..."
        )

        time.sleep(wait_seconds)

    def run_daily_scheduler(self):
        """Run the daily scheduler loop"""

        while True:
            try:
                # Wait until 00:05 UTC
                self.wait_until_next_run()

                # Push yesterday's data
                yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).strftime(
                    "%Y-%m-%d"
                )
                logger.info(f"Running scheduled push for {yesterday}")
                self.push_metrics_for_date(yesterday)

            except KeyboardInterrupt:
                logger.info("Scheduler stopped by user")
                break
            except Exception as e:
                logger.error(f"Error in scheduler loop: {e}", exc_info=True)
                # Wait a bit before retrying
                time.sleep(60)


def main():
    """Main entry point"""
    logger.info("=" * 50)
    logger.info("Node Rewards Ingester for VictoriaMetrics")
    logger.info("=" * 50)
    logger.info("")

    # Get configuration from environment
    victoria_url = os.environ.get("VICTORIA_METRICS_URL", "http://localhost:9090")

    # Create pusher
    pusher = NodeRewardsPusher(victoria_url)

    # Wait for VictoriaMetrics
    pusher.wait_for_victoria_metrics()

    # Backfill historical data
    pusher.backfill(days=40)

    # Run daily scheduler
    pusher.run_daily_scheduler()


if __name__ == "__main__":
    main()

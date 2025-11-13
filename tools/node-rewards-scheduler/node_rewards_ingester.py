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


IC_URL = "https://ic0.app"

# These have to be tuples
NODE_REWARDS_CANISTER_IDS = [
    ("uuew5-iiaaa-aaaaa-qbx4q-cai"),  # Dev
    # TODO: uncomment to enable prod
    # ("sgymv-uiaaa-aaaaa-aaaia-cai"),  # Prod
]
GOVERNANCE_CANISTER_ID = "rrkah-fqaaa-aaaaa-aaaaq-cai"  # NNS Governance canister

###################### TYPE DEFINITIONS ###########################
DATE_UTC_TYPE = Types.Record(
    {
        "year": Types.Nat32,
        "month": Types.Nat32,
        "day": Types.Nat32,
    }
)

GET_REWARDS_DAILY_REQUEST_TYPE = Types.Record({"day": DATE_UTC_TYPE})

NODE_METRICS_DAILY_TYPE = Types.Record(
    {
        "subnet_assigned": Types.Opt(Types.Principal),
        "subnet_assigned_failure_rate": Types.Opt(Types.Float64),
        "num_blocks_proposed": Types.Opt(Types.Nat64),
        "num_blocks_failed": Types.Opt(Types.Nat64),
        "original_failure_rate": Types.Opt(Types.Float64),
        "relative_failure_rate": Types.Opt(Types.Float64),
    }
)

DAILY_NODE_FAILURE_RATE_TYPE = Types.Variant(
    {
        "SubnetMember": Types.Record(
            {
                "node_metrics": Types.Opt(NODE_METRICS_DAILY_TYPE),
            }
        ),
        "NonSubnetMember": Types.Record(
            {
                "extrapolated_failure_rate": Types.Opt(Types.Float64),
            }
        ),
    }
)

DAILY_NODE_REWARDS_TYPE = Types.Record(
    {
        "node_id": Types.Opt(Types.Principal),
        "node_reward_type": Types.Opt(Types.Text),
        "region": Types.Opt(Types.Text),
        "dc_id": Types.Opt(Types.Text),
        "daily_node_failure_rate": Types.Opt(DAILY_NODE_FAILURE_RATE_TYPE),
        "performance_multiplier": Types.Opt(Types.Float64),
        "rewards_reduction": Types.Opt(Types.Float64),
        "base_rewards_xdr_permyriad": Types.Opt(Types.Float64),
        "adjusted_rewards_xdr_permyriad": Types.Opt(Types.Float64),
    }
)

NODE_TYPE_REGION_BASE_REWARDS_TYPE = Types.Record(
    {
        "monthly_xdr_permyriad": Types.Opt(Types.Float64),
        "daily_xdr_permyriad": Types.Opt(Types.Float64),
        "node_reward_type": Types.Opt(Types.Text),
        "region": Types.Opt(Types.Text),
    }
)

TYPE3_REGION_BASE_REWARDS_TYPE = Types.Record(
    {
        "region": Types.Opt(Types.Text),
        "nodes_count": Types.Opt(Types.Nat64),
        "avg_rewards_xdr_permyriad": Types.Opt(Types.Float64),
        "avg_coefficient": Types.Opt(Types.Float64),
        "daily_xdr_permyriad": Types.Opt(Types.Float64),
    }
)

DAILY_NODE_PROVIDER_REWARDS_TYPE = Types.Record(
    {
        "total_base_rewards_xdr_permyriad": Types.Opt(Types.Nat64),
        "total_adjusted_rewards_xdr_permyriad": Types.Opt(Types.Nat64),
        "base_rewards": Types.Vec(NODE_TYPE_REGION_BASE_REWARDS_TYPE),
        "base_rewards_type3": Types.Vec(TYPE3_REGION_BASE_REWARDS_TYPE),
        "daily_nodes_rewards": Types.Vec(DAILY_NODE_REWARDS_TYPE),
    }
)

DAILY_RESULTS_TYPE = Types.Record(
    {
        "subnets_failure_rate": Types.Vec(Types.Tuple(Types.Principal, Types.Float64)),
        "provider_results": Types.Vec(
            Types.Tuple(Types.Principal, DAILY_NODE_PROVIDER_REWARDS_TYPE)
        ),
    }
)

RETURN_TYPE = Types.Variant(
    {
        "Ok": DAILY_RESULTS_TYPE,
        "Err": Types.Text,
    }
)

LIST_NODE_PROVIDER_REWARDS_REQUEST_TYPE = Types.Record(
    {"date_filter": Types.Opt(Types.Nat64)}
)


class NodeRewardsClient:
    """Client for interacting with the node rewards canister"""

    def __init__(self, ic_url: str, canister_id: str):
        # Create anonymous identity
        self.identity = Identity()
        self.client = Client(url=ic_url)
        self.agent = Agent(self.identity, self.client)
        self.canister_id = canister_id

    def get_rewards_daily(self, date: str) -> Dict[str, Any]:
        """Fetch daily rewards data from node rewards canister"""
        parsed_date = datetime.strptime(date, "%Y-%m-%d")
        arg_value = {
            "day": {
                "year": parsed_date.year,
                "month": parsed_date.month,
                "day": parsed_date.day,
            }
        }
        arg_bytes = encode(
            [{"type": GET_REWARDS_DAILY_REQUEST_TYPE, "value": arg_value}]
        )

        response = self.agent.query_raw(
            self.canister_id,
            "get_node_providers_rewards_calculation",
            arg_bytes,
            RETURN_TYPE,
        )

        if not response or len(response) == 0:
            logger.error(f"Empty response for {date}")
            return {}

        result = response[0].get("value", {})

        if "Err" in result:
            error_msg = result["Err"]
            logger.error(f"Canister returned error for {date}: {error_msg}")
            return {}

        if "Ok" not in result:
            raise ValueError(
                f"Unexpected result, contains neither `Err` nur `Ok`: {result}"
            )

        daily_results = result["Ok"]

        # Convert lists of tuples to dictionaries for easier processing
        # provider_results: [[Principal, {...}], ...] -> {Principal: {...}}
        provider_results_dict = {}
        for principal, provider_data in daily_results.get("provider_results", []):
            provider_results_dict[str(principal)] = provider_data

        # subnets_failure_rate: [[Principal, float], ...] -> {Principal: float}
        subnets_failure_rate_dict = {}
        for principal, failure_rate in daily_results.get("subnets_failure_rate", []):
            subnets_failure_rate_dict[str(principal)] = failure_rate

        result_dict = {
            "provider_results": provider_results_dict,
            "subnets_failure_rate": subnets_failure_rate_dict,
        }

        logger.info(
            f"Successfully fetched rewards for {date} ({len(provider_results_dict)} providers)"
        )
        return result_dict

    def get_latest_governance_reward_event(self) -> Optional[float]:
        """Fetch latest governance reward event timestamp from governance canister"""

        arg_bytes = encode(
            [
                {
                    "type": LIST_NODE_PROVIDER_REWARDS_REQUEST_TYPE,
                    "value": {
                        "date_filter": []  # Empty list = None for optional types
                    },
                }
            ]
        )

        response = self.agent.query_raw(
            GOVERNANCE_CANISTER_ID,
            "list_node_provider_rewards",
            arg_bytes,
        )

        if not response or len(response) == 0:
            logger.warning("Empty response from governance canister")
            return None

        result = response[0].get("value", {})
        rewards_list = result.get("rewards", [])

        if rewards_list and len(rewards_list) > 0:
            first_reward = rewards_list[0]
            timestamp = first_reward.get("timestamp")
            if timestamp:
                logger.info(f"Latest governance reward timestamp: {timestamp}")
                return float(timestamp)

        return None


class NodeRewardsPusher:
    """Pushes node rewards metrics to VictoriaMetrics"""

    def __init__(self, victoria_url: str):
        self.victoria_url = victoria_url
        self.nrc_clients = [
            NodeRewardsClient(IC_URL, c) for c in NODE_REWARDS_CANISTER_IDS
        ]

    @staticmethod
    def _unwrap_optional(value):
        """Unwrap Candid optional values (represented as lists)"""
        if isinstance(value, list):
            return value[0] if len(value) > 0 else None
        return value

    @staticmethod
    def _make_line(metric_name: str, value: int, ts: int, **kwargs) -> str:
        return f"{metric_name}{{ {', '.join([f'{key}="{value}"' for key, value in kwargs.items()])} }} {value} {ts}"

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

    def push_metrics_for_date(self, date: str):
        """
        Fetch node rewards data from IC canisters and push to VictoriaMetrics for a specific date
        Returns True if successful, False otherwise
        """

        logger.info(f"Pushing node rewards data for {date}")
        target_date = datetime.strptime(date, "%Y-%m-%d")

        noon = target_date.replace(hour=12, minute=0, second=0, microsecond=0)
        noon_timestamp_ms = int(noon.replace(tzinfo=timezone.utc).timestamp() * 1000)

        metrics_lines = []
        for client in self.nrc_clients:
            daily_results = client.get_rewards_daily(date)

            if not daily_results:
                raise ValueError(f"⚠️  No data available for {date}")

            # Helper function to not repeat the labels all the
            # time and to single out the place for changing labels
            def add_line_helper(metric_name: str, value, **kwargs):
                metrics_lines.append(
                    self._make_line(
                        metric_name,
                        value,
                        noon_timestamp_ms,
                        canister_id=client.canister_id,
                        **kwargs,
                    )
                )

            # Provider-level metrics
            provider_results = daily_results.get("provider_results", {})
            for provider_id, provider_rewards in provider_results.items():
                provider_id_str = str(provider_id)

                def add_line_helper_with_provider(
                    metric_name: str, value: int, **kwargs
                ):
                    add_line_helper(
                        metric_name, value, provider_id=provider_id_str, **kwargs
                    )

                # nodes_count
                nodes_count = len(provider_rewards.get("daily_nodes_rewards", []))
                add_line_helper_with_provider("nodes_count", nodes_count)

                # base_rewards
                base_rewards = self._unwrap_optional(
                    provider_rewards.get("total_base_rewards_xdr_permyriad")
                )
                if base_rewards is not None:
                    add_line_helper_with_provider(
                        "total_base_rewards_xdr_permyriad", base_rewards
                    )

                adjusted_rewards = self._unwrap_optional(
                    provider_rewards.get("total_adjusted_rewards_xdr_permyriad")
                )
                if adjusted_rewards is not None:
                    add_line_helper_with_provider(
                        "total_adjusted_rewards_xdr_permyriad", adjusted_rewards
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

                        if not node_metrics:
                            continue

                        subnet_id = self._unwrap_optional(
                            node_metrics.get("subnet_assigned")
                        )
                        subnet_id_str = str(subnet_id) if subnet_id else ""

                        # original_failure_rate
                        original_fr = self._unwrap_optional(
                            node_metrics.get("original_failure_rate")
                        )
                        if original_fr is not None:
                            add_line_helper_with_provider(
                                "original_failure_rate",
                                original_fr,
                                node_id=node_id_str,
                                subnet_id=subnet_id_str,
                            )

                        # relative_failure_rate
                        relative_fr = self._unwrap_optional(
                            node_metrics.get("relative_failure_rate")
                        )
                        if relative_fr is not None:
                            add_line_helper_with_provider(
                                "relative_failure_rate",
                                relative_fr,
                                node_id=node_id_str,
                                subnet_id=subnet_id_str,
                            )

            # Subnet-level metrics
            subnets_failure_rate = daily_results.get("subnets_failure_rate", {})
            for subnet_id, failure_rate in subnets_failure_rate.items():
                subnet_id_str = str(subnet_id)
                metrics_lines.append(
                    f'subnet_failure_rate{{subnet_id="{subnet_id_str}"}} {failure_rate} {noon_timestamp_ms}'
                )
                add_line_helper(
                    "subnets_failure_rate", failure_rate, subnet_id=subnet_id_str
                )

            # Governance timestamp
            gov_timestamp = self.nrc_clients[0].get_latest_governance_reward_event()
            if gov_timestamp:
                add_line_helper(
                    "governance_latest_reward_event_timestamp_seconds", gov_timestamp
                )

        if not metrics_lines:
            raise ValueError("After evaluation there were no metrics to upload")

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
        try:
            response.raise_for_status()
        except Exception:
            logger.error(
                f"❌ Failed to push to VictoriaMetrics: {response.status_code} - {response.text}"
            )
            raise

        logger.info(
            f"✅ Successfully pushed data for {date} ({len(metrics_lines)} metrics)"
        )

    def backfill(self, days: int = 40):
        """Backfill historical data"""

        logger.info(f"Starting backfill of last {days} days...")

        for i in range(days, 0, -1):
            date = datetime.now(timezone.utc) - timedelta(days=i)
            date = date.strftime("%Y-%m-%d")

            logger.info(f"[{days - i + 1:2d}/{days}] Backfilling data for {date}...")
            try:
                self.push_metrics_for_date(date)
            except Exception as e:
                logger.error(f"Failed to backfill data due to: {e}")

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

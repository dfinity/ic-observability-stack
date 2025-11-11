import argparse
import urllib.parse

import yaml


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        "prom-config-builder",
        description="Used to expand the configuration to actual victoria-metrics config",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument(
        "--template-path",
        dest="template_path",
        default="/config/victoria-metrics/config-template.yaml",
        help="Path to the config template that should be expanded",
    )

    parser.add_argument(
        "--output-path",
        dest="output_path",
        default="/config/victoria-metrics/config.yaml",
        help="Path to where the output should be written",
    )

    parser.add_argument(
        "--node-provider-id",
        dest="node_provider_id",
        help="The principal id for the node provider",
    )

    parser.add_argument(
        "--dc-id",
        dest="dc_id",
        default=None,
        help="The data center id represented with two letters and a number",
    )

    parser.add_argument(
        "--sd-url",
        dest="sd_url",
        default="localhost:8000",
        help="Override the host for multiservice-discovery container. If not running in network_mode: host it will be multiservice-discovery:8000",
    )

    return parser.parse_args()


def expand_anchors_text(yaml_text: str) -> str:
    data = yaml.safe_load(yaml_text)

    class NoAliasDumper(yaml.SafeDumper):
        # always return True to *prevent* YAML from emitting aliases
        def ignore_aliases(self, data):
            return True

    return yaml.dump(
        data, Dumper=NoAliasDumper, default_flow_style=False, sort_keys=False
    )


if __name__ == "__main__":
    args = parse_args()

    with open(args.template_path, "r") as f:
        text = f.read()
        template = dict(yaml.safe_load(expand_anchors_text(text)))

    for scrape_config in template["scrape_configs"]:
        job_name = scrape_config["job_name"]

        # Restrict job
        scrape_config["relabel_configs"][2]["regex"] = job_name

        url = scrape_config["http_sd_configs"][0]["url"]
        params = {"node_provider_id": args.node_provider_id}
        if args.dc_id is not None:
            params["dc_id"] = args.dc_id

        url_parts = urllib.parse.urlparse(url)
        encoded_query = urllib.parse.urlencode(params)

        scrape_config["http_sd_configs"][0]["url"] = urllib.parse.urlunparse(
            url_parts._replace(query=encoded_query, netloc=args.sd_url)
        )

    # Drop anchors
    del template["anchors"]

    with open(args.output_path, "w") as f:
        f.write(yaml.safe_dump(template))

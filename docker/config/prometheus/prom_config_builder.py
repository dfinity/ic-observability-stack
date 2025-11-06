import argparse

import yaml


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        "prom-config-builder",
        description="Used to expand the configuration to actual prometheus config",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument(
        "--template-path",
        dest="template_path",
        default="/config/prometheus/config-template.yaml",
        help="Path to the config template that should be expanded",
    )

    parser.add_argument(
        "--output-path",
        dest="output_path",
        default="/config/prometheus/config.yaml",
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
        url = f"{url}?node_provider_id={args.node_provider_id}{'&dc_id={dc_id}'.format(dc_id=args.dc_id) if args.dc_id is not None else ''}"
        scrape_config["http_sd_configs"][0]["url"] = url

    # Drop anchors
    del template["anchors"]

    with open(args.output_path, "w") as f:
        f.write(yaml.safe_dump(template))

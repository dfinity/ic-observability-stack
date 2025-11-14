# Upgrading the IC Observability Stack

This guide details the procedure for updating your existing deployment of **IC Observability Stack** to the latest version. Since the stack is provisioned using Docker, the upgrade process is generally safe, as all of the resources coming from this repository are codified and don't conflict with each other.

**Disclaimer**: If you make your changes, either in Grafana using the UI or changes in the code there may be conflicts. More about resolving conflicts [here](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/addressing-merge-conflicts/resolving-a-merge-conflict-using-the-command-line).

## Prerequsites

Before starting the upgrade, ensure your system is ready:
1. *Clean Working Directory*: Ensure you have commited or stashed any local changes to the repository before pulling updates. To see if that is needed conslut the panel showing the [State of the directory](http://localhost:3000/d/robv9sv/observability-stack-github-status?orgId=1&from=now-6h&to=now&timezone=browser&refresh=10s&viewPanel=panel-6) or run the command:
```bash
git status
# If there are any changes you can pick to commit or stash them.
```
2. Turn off the stack:
```bash
docker compose down
```

## Step 1: Pull the latest repository changes

Navigate to the root directory (where this file is located) and fetch the latest code from the upstream branch:
```bash
git pull origin master
```
This command will fetch and merge any new Dockerfiles, configuration files, or any other dependency updates int your local working copy. 

## Step 2: Update Local dependecies (setup)

After every upgrade run the `setup.sh` to ensure that your environment is configured to work with the latest version of the stack properly. Navigate to the root directory (where this file is located) and run setup like the following:
```bash
./setup.sh
```

## Step 3: Spin the services back up

Now that you have the newest version locally you can run the following command to bring the services back up:
```bash
# This will create the docker containers.
docker compose up -d
```

## Step 4: Verify the services

After the services are back up you should:
* Check that victoria metrics [can scrape targets](http://localhost:9090/targets?search=)
* Check that you [can access grafana](http://localhost:3000)
* Check if there are any services that aren't running:
```bash
docker compose ps --format json | jq 'select(.State != "running") | {name: .Name, status: .Status, exitCode: .ExitCode}'
```

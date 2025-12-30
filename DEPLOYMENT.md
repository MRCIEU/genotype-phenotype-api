# Deployment and Production

There are 2 sides to gpmap deployment, code, and data

## Code Deployment

### Docker Swarm

To add another server to production, there is a guide in the wiki in how to deploy and configure the Oracle server.

Here are the steps after the server is available:

*Leave and Join A Docker Swarm*


To create a swarm, you must choose a server node to be a 'manager', and initalise the swarm

```sudo docker swarm init --advertise-addr <private-ip-address-of-server>```

You will also need to manually create the network

```docker network create --driver=overlay --attachable gpmap_network```

This will create a `sudo docker swarm join` command, for you to copy, and run on the node you want to join the swarm.  You will also want to create a label for the new node

```sudo docker node update --label-add type=special-box <api|upload>```

We currently have two types of nodes, one to run the api/nginx/redis, and the other to run the upload worker.  Add the new box to one of these.

* Check membership of swarm `sudo docker node ls`
* List what is running on the stack: `sudo docker stack ps gpmap`
* Run to leave a docker swarm: `sudo docker swarm leave`
* Destroy the docker swarm and start again: `sudo docker stack rm gpmap`

### Deploy Code Changes

There is a helper script that will update the code and restart: `./update_code_and_restart.sh`

Essentially

sudo docker stack deploy -c docker-swarm.yml gpmap --resolve-image always --prune

### Docker swarm errors

If there are problems when trying to update the docker swarm config / images, check here

* ```sudo docker stack ps gpmap --no-trunc```: Look at the "CURRENT STATE" and "ERROR" columns.  Rejected usually means scaling issue Preparing (for a long time) might mean failing to pull image.
* ```sudo docker service ps gpmap_api```
* ```sudo docker service logs -f --tail 50 gpmap_api```: you can also look at the container logs
* ```sudo docker service inspect gpmap_api --format '{{.Spec.TaskTemplate.ContainerSpec.Image}}'```: verify image version

## Data and Code Deployment

All of the data for this project gets created on ieu-p1

There is a script in `genotype-phenotype-map` that allows you to move data from the pipeline onto the servers, please look at this file

```Rscript sync_to_servers.R --different-options```

This moves the data, and you can choose just to move what has changed.  Afterwards, there is a script on the manager server to update the data on the servers and restart the containers.

`./update_data_update_code_restart.sh`

Similarly, if there was a problem with the data, you can rollback (only the db files) and restart

`./rollback_data_update_code_restart.sh`
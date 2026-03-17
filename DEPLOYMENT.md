# Deployment and Production

There are 2 sides to gpmap deployment, code, and data

## Code Deployment

### Deploy Code Changes

Once you have merged in your changes to `main`, and the CI pipeline has been run, you are ready to deploy your code.  We use Docker Swarm to deploy our changes, docker swarm has a 'Leader' node.  This is the server that you have to run all the commands from.  It is currently the server which is called `ORACLE_SERVER` in the GitHub actions environment variables.

There are a series of scripts that help with managing deployment.  All of these scripts are copied over to the "main" oracle server

Docker swarm 

* `update_code_and_restart.sh`: this will run the docker swarm deployment script which will deploy the latest docker containers
* `update_data_update_code_restart.sh`: this is used when you have update the database files ([see this wiki](https://github.com/MRCIEU/genotype-phenotype-map/wiki/Pipeline-Output:-Sync-and-Backup)).  Copies over database files, updates containers, refreshes the redis cache.
* `rollback_data_update_code_restart.sh`: Takes old db files, and recopies them, updates containers


### Managing the GWAS Upload Queue

The 'process GWAS' pipeline allows users to upload their own data, there are a series of API endpoints that allow us to control this pipeline

* `./manage_queue.sh retry-dlq <guid>`: Retries a specific GWAS upload that failed
* `./manage_queue.sh delete-gwas <guid>`: Deletes GWAS from database, oracle bucket, and upload server
* `./manage_queue.sh delete-all-dlq`: Delete all messages from the DLQ


### Renewing the SSL certificate

If you deploy new code, the SSL cert will automatically be done.  However, if it isn't, there is a script `./refresh_ssl_certs.sh`

This will run certbot, and restart the docker instances.  Importantly, the nginx frontend, which will pick up the new cert.


### Docker swarm errors

If there are problems when trying to update the docker swarm config / images, check here


* ```sudo docker stack ps gpmap --no-trunc```: Look at the "CURRENT STATE" and "ERROR" columns.  Rejected usually means scaling issue Preparing (for a long time) might mean failing to pull image.
* ```sudo docker service ps gpmap_api```
* ```sudo docker service logs -f --tail 50 gpmap_api```: you can also look at the container logs
* ```sudo docker service inspect gpmap_api --format '{{.Spec.TaskTemplate.ContainerSpec.Image}}'```: verify image version
* ```sudo docker service update --force gpmap_gwas_upload_worker```: if the upload worker just stopped.


## Upload Server Configuration

You may want to increase the swap on each server, to do this
```
# 1. Create a 12GB file named 'extraswap' in the root directory
sudo fallocate -l 12G /extraswap
# 2. Set strict permissions so only the root user can read it
sudo chmod 600 /extraswap
# 3. Format the file to be used as swap
sudo mkswap /extraswap
# 4. Activate the swap file immediately
sudo swapon /extraswap
```

## Docker Swarm Configuration

To add another server to production, there is a [guide in the wiki](https://github.com/MRCIEU/genotype-phenotype-api/wiki/Public-Website-and-Oracle-Cloud) on how to deploy and configure an Oracle server.

Here are the steps after the server is available:

*Leave and Join A Docker Swarm*

To create a swarm, you must choose a server node to be a 'manager', and initalise the swarm

```
sudo docker swarm init --advertise-addr <private-ip-address-of-server>
sudo docker swarm update --task-history-limit 2
```

You will also need to manually create the network

```docker network create --driver=overlay --attachable gpmap_network```

This will create a `sudo docker swarm join` command, for you to copy, and run on the node you want to join the swarm.  You will also want to create a label for the new node.  You can get that join command again by `sudo docker swarm join-token worker`

```sudo docker node update --label-add type=<api|upload> <name_of_node>```

We currently have two types of nodes, one to run the api/nginx/redis, and the other to run the upload worker.  Add the new box to one of these.

* Check membership of swarm `sudo docker node ls`
* List what is running on the stack: `sudo docker stack ps gpmap`
* Run to leave a docker swarm: `sudo docker swarm leave`
* Destroy the docker stack and start again: `sudo docker stack rm gpmap`

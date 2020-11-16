#/bin/bash
#
# Author: R.Szmurlo 2020
#

IMAGE_NAME=szmurlor/rass2:0.9
USAGE="./run-docker-dev.sh [-h] [--name IMAGE_NAME] 

The script first checks if a docker image with name IMAGE_NAME exists. If not then it 
builds a new image using docker/Dockerfile specification. Then the IMAGE_NAME is 
run with interactive mode and with an attached current folder into /rass2-dev folder.

Arguments:
  -h            displays this help
  --name IMAGE  overrides the default value of the image which is $IMAGE_NAME
"

argc=$#
argv=("$@")

for (( i=0; i<argc; i++ )); do
       if [ "--name" == "${argv[i]}" ]; then
	       IMAGE_NAME=${argv[i+1]}
       fi
       if [ "-h" == "${argv[i]}" ]; then
	       echo "$USAGE"
	       exit 0
       fi
done

IMAGE_ID=$(docker image ls $IMAGE_NAME -q)
if [ -z "$IMAGE_ID" ]; then
	docker build -t $IMAGE_NAME -f docker/Dockerfile .
	IMAGE_ID=$(docker image ls $IMAGE_NAME -q)
else
	echo "Found docker image $IMAGE_NAME with ID: $IMAGE_ID"
fi
echo "Starting image $IMAGE_NAME with ID: $IMAGE_ID"
docker run -ti -w="/rass2-dev" -v $(pwd):/rass2-dev -p5000:5000 $IMAGE_ID 

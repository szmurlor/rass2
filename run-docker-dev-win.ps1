#/bin/bash
#
# Author: R.Szmurlo 2019
#

#IMAGE_NAME=szmurlor/rass2:0.6
#IMAGE_ID=$(docker image ls $IMAGE_NAME -q)
echo "Starting image $IMAGE_NAME with ID: $IMAGE_ID"
#docker run -ti -w="/rass2-dev" -v "$c:/rass2-dev" $IMAGE_ID 

docker run -ti -w="/rass2-dev" -p 5000:5000 -v "$(pwd):/rass2-dev" szmurlor/rass2:0.6 
cmd /c pause
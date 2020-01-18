#
# Author: R.Szmurlo 2019
#

$IMAGE_NAME='szmurlor/rass2:0.6'

$USAGE="./run-docker-dev.ps1 [-h] [--name IMAGE_NAME] 

First script checks if a docker image with name IMAGE_NAME exists. If not then it 
builds a new image using docker/Dockerfile specification. Then the IMAGE_NAME is 
run with interactive mode and with an attached current folder into /rass2-dev folder.

Arguments:
  -h            displays this help
  --name IMAGE  overrides the default value of the image which is $IMAGE_NAME
"

$argc=$args.count
$argv=$args

for ( $i = 0; $i -lt $args.count; $i++ ) {
    if ($args[ $i ] -eq "/n"){ $strName=$args[ $i+1 ]}
    if ($args[ $i ] -eq "-n"){ $strName=$args[ $i+1 ]}
    if ($args[ $i ] -eq "/d"){ $strDomain=$args[ $i+1 ]}
    if ($args[ $i ] -eq "-d"){ $strDomain=$args[ $i+1 ]}
}
Write-Host $strName
Write-Host $strDomain

for ( $i=0; $i -lt $argc; $i++ ) {
    if ( "--name" -eq $argv[ $i ] ) {
	    $IMAGE_NAME = $argv[ $i+1 ]
    }
    if ( "-h" -eq $argv[ $i ] ) {
	   write-host "$USAGE"
	   exit 0
    }
}

$IMAGE_ID=$(docker image ls $IMAGE_NAME -q)
if ( !$IMAGE_ID ) {
    write-host "Attempting to build image $IMAGE_NAME with definition form file docker/Dockerfile"
    & docker build -t $IMAGE_NAME -f docker/Dockerfile .
	$IMAGE_ID=$(docker image ls $IMAGE_NAME -q)
} else {
	write-host "Found docker image $IMAGE_NAME with ID: $IMAGE_ID"
}

if ($IMAGE_ID) {
    write-host "Starting image $IMAGE_NAME with ID: $IMAGE_ID"
    $pwd = $(Get-Location).toString()
    # write-host "Current dir: $pwd"
    $vol = $pwd + ":/rass2-dev"
    # write-host "Volume to mount: $vol"
    & docker run -ti -w="/rass2-dev" -p 5000:5000 -v "$vol" $IMAGE_ID 
} else {
    write-host "ERROR! Unable to locate image name: $IMAGE_NAME in the docker"
}

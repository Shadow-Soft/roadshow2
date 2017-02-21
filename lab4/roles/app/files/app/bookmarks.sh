# Starts, Stops and Builds DevopsBookmarks instance

USER=securepaas
IMAGE_NAME=devops

buildImage() {
	status > /dev/null
	if [ $? == 3 ];
	then 
		echo "Building new image"
		docker build -t $IMAGE_NAME ./
		return 0
	else
		echo "Image already exists"
		return 1
	fi
}

reBuildImage() {
	removeImage > /dev/null
	buildImage
}


runContainer() {
	status > /dev/null
	if [ $? == 2 ]; 
	then 
		echo "Running image for the first time"
		docker run -idt -p 3000:3000 --name=$IMAGE_NAME $IMAGE_NAME
		return 0
	else
		echo "Image was ran previously"
		return 1
	fi
}

startContainer() {
	status > /dev/null
	RESULT=$?
	if [ $RESULT == 1 ]; 
	then 
		echo "Starting $IMAGE_NAME"
		docker start $IMAGE_NAME
		return 0
	elif [ $RESULT == 2 ];
	then
		runImage
	elif [ $RESULT == 3 ];
	then
		buildImage
		runImage
	else
		echo "$IMAGE_NAME is already running"
		return 1
	fi
}

stopContainer() {
	status > /dev/null
	RESULT=$?
	if [ $RESULT == 0 ]; 
	then 
		echo "Stopping $IMAGE_NAME"
		docker stop $IMAGE_NAME
		return 0
	elif [ $RESULT == 1 ] || [ $RESULT == 2 ];
	then
		echo "$IMAGE_NAME isn't running"
		return 1
	else
		echo "$IMAGE_NAME doesn't exist"
		return 1
	fi
}

removeContainer() {
	stopContainer > /dev/null
	status > /dev/null
	RESULT=$?
	if [ $RESULT != 2 ] || [ $RESULT != 3 ]; 
	then 
		echo "Removing $IMAGE_NAME"
		docker rm $IMAGE_NAME
		return 0
	else
		echo "$IMAGE_NAME doesn't exist"
		return 1
	fi
}

removeImage() {
	removeContainer > /dev/null
	status > /dev/null
	if [ $? != 3 ]; 
	then 
		echo "Removing $IMAGE_NAME image"
		docker rmi $IMAGE_NAME
		return 0
	else
		echo "$IMAGE_NAME image doesn't exist"
		return 1
	fi
}

status() {
	if isImageRunning $1; 
	then 
		echo "$IMAGE_NAME is running"
		return 0
	else	
		if imageExists $1;
		then
			if hasImageEverRun $1;
			then
				echo "$IMAGE_NAME isn't running"
				return 1
			else
				echo "$IMAGE_NAME has never run"
				return 2
			fi
		else
			echo "$IMAGE_NAME image doesn't exist"
			return 3
		fi
	fi

}

imageExists() {
	EXISTS=$(docker images | grep $IMAGE_NAME) 
	EXISTS=$(echo $EXISTS | awk '{print $1}')
	if [ $EXISTS ];
	then
		return 0
	else
		return 1
	fi
}

hasImageEverRun() {
	PROCESS=$(docker ps -a | grep $IMAGE_NAME)
	PROCESS=$(echo $PROCESS | awk '{print $1}')
	if [ $PROCESS ];
	then
		return 0
	else
		return 1
	fi
}

isImageRunning() {
	PROCESS=$(docker ps | grep $IMAGE_NAME)
	PROCESS=$(echo $PROCESS | awk '{print $1}')
	if [ $PROCESS ];
	then
		return 0
	else
		return 1
	fi
}


# See how we were called.
case "$1" in
  build)
	buildImage
	;;
  rebuild)
	reBuildImage
	;;
  run)
	runContainer
	;;
  start)
	startContainer
	;;
  stop)
	stopContainer
	;;
  rm)
	removeContainer
	;;
  rmi)
	removeImage
	;;
  status)
	status
	;;
  *)
	echo $"Usage: $0 {build | rebuild | run | start | stop | rm | rmi | status}"
	exit 1
esac

exit $?

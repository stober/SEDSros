#!/bin/bash

# This is the master script for recording, training, then driving the robot using SEDS-based control.

function launch_silent {
    roslaunch $1 $2 >> /tmp/seds.out 2>> /tmp/seds.err
}

function record_bag {
    # a simple function that records /tf in a specified directory
    cd $1
    echo "Prepare to record demonstration number $2 in directory $1."
    echo "Press enter to begin demonstration. When the demonstration is complete press enter again."

    read
    rosbag record /tf &
    ID=$!

    read
    kill -2 $ID # send a SIGINT signal to kill the recording process

    # return to original directory
    cd -
}

function run_demo {
    ndemo=1
    OPTIONS="Record Learn Run Quit"
    while [ 1 ]; do

      #clear
      echo "Please select one of the following options."
      select opt in $OPTIONS; do
	if [ "$opt" = "Quit" ]; then
	  echo "Quiting..."
	  exit
	elif [ "$opt" = "Record" ]; then
	  record_bag $ddir $ndemo
	  let ndemo=ndemo+1
	elif [ "$opt" = "Learn" ]; then

	    echo "Beginning the training process!"
	    echo "Processing the demonstration bagfiles..."

	    rosrun seds tf2seds.py -b $ddir -o /tmp/tmp.bag

	    echo "Learning new model parameters using seds!"

            # optimization
	    rosservice call /seds/optimize /tmp/tmp.bag

            # load model parameters into ds_node
	    rosservice call /ds_node/load_model

	    echo "Model is learned and loaded."
	  break
	elif [ "$opt" = "Run" ]; then

	    echo "Press enter to start the r_cart controller."

	    read
	    rosrun pr2_controller_manager pr2_controller_manager start r_cart

	    echo "Press enter to begin to drive the robot using the model."

	    read
	    rosservice call /pr2_driver/start

	    echo "Press enter again to stop the robot."

	    read
	    rosservice call /pr2_driver/stop

	    echo "Stopping the r_cart controller."
	    rosrun pr2_controller_manager pr2_controller_manager stop r_cart

	else
	  #clear
	  echo "Bad option!"
	fi
      done
    done
}

# The script requires a working directory.
ddir=$1

mkdir -p $ddir

# This starts up the low-level topic-based cartesian control system (but turns off all pr2 controllers).
# launch_silent seds jtteleop.launch &

# This starts up seds and ds and pr2_driver nodes which will be used for learning and controlling the robot.
launch_silent seds pr2.launch &

# Stop the controller for the moment while we record bagfiles.
# rosrun pr2_controller_manager pr2_controller_manager stop r_cart

# Run the demo.
run_demo


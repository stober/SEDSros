#! /usr/bin/env python
"""
Author: Jeremy M. Stober
Program: PUBLISH_RCART.PY
Date: Wednesday, June 22 2011
Description: Publish single command to r_cart topic.
"""

import roslib
roslib.load_manifest('seds')
import rospy
from geometry_msgs.msg import PoseStamped
import sys
import json

if __name__ == '__main__':

    x = json.loads(sys.argv[1])

    print "Moving to new coords: ", str(x)

    rospy.init_node("publish_rcart")
    pub = rospy.Publisher('r_cart/command_pose', PoseStamped)
    cmd = PoseStamped()

    cmd.header.frame_id = "/torso_lift_link"
    cmd.pose.position.x = x[0]
    cmd.pose.position.y = x[1]
    cmd.pose.position.z = x[2]
    cmd.pose.orientation.x = x[3]
    cmd.pose.orientation.y = x[4]
    cmd.pose.orientation.z = x[5]
    cmd.pose.orientation.w = x[6]

    rate = rospy.Rate(10)
    while not rospy.is_shutdown():

        rospy.loginfo( "Publishing cmd: %s" % str(cmd))
        pub.publish(cmd)
        rate.sleep()

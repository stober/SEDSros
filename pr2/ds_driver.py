#! /usr/bin/env python
"""
Author: Jeremy M. Stober
Program: CAT_TRANSFORM.PY
Date: Monday, June 20 2011
Description: Script to display the latest available tf transform in easy to parse format.
"""

import roslib
roslib.load_manifest('tf')
roslib.load_manifest('seds')

import tf
import rospy
import rospy.rostime as rostime
from geometry_msgs.msg import PoseStamped
from seds.srv import DSSrv
import numpy
npa = numpy.array

if __name__ == '__main__':

    source_frameid = 'torso_lift_link'
    target_frameid = 'r_gripper_tool_frame'

    rospy.init_node('ds_driver')
    listener = tf.TransformListener()
    pub = rospy.Publisher('r_cart/command_pose', PoseStamped)

    # wait for the ds server
    rospy.wait_for_service('ds_server')
    ds = rospy.ServiceProxy('ds_server', DSSrv) # the running model

    # waits 10 secs for the source and target frames to become available
    try:
        listener.waitForTransform(source_frame=source_frameid, target_frame=target_frameid,
                                  time=rostime.Time(0), timeout=rospy.Duration(10.0))
    except tf.Exception, error:
        print error

    cmd = PoseStamped()
    cmd.header.frame_id = "/torso_lift_link"
    rate = rospy.Rate(10) # 10Hz
    while not rospy.is_shutdown():

        et = listener.lookupTransform(source_frameid, target_frameid, rostime.Time(0))
        t = listener.getLatestCommonTime(source_frameid, target_frameid)
        x = list(et[0][:] + et[1][:])
        dx = list(ds(x).dx)

        rospy.loginfo("x: %s" % str(x))
        rospy.loginfo("dx: %s" % str(dx))
        newx = list(npa(x) + npa(dx))

        rospy.loginfo("nx: %s" % str(newx))

        cmd.pose.position.x = newx[0]
        cmd.pose.position.y = newx[1]
        cmd.pose.position.z = newx[2]
        cmd.pose.orientation.x = x[3]
        cmd.pose.orientation.y = x[4]
        cmd.pose.orientation.z = x[5]
        cmd.pose.orientation.w = x[6]
        #cmd.pose.orientation.x = newx[3]
        #cmd.pose.orientation.y = newx[4]
        #cmd.pose.orientation.z = newx[5]
        #cmd.pose.orientation.w = newx[6]

        pub.publish(cmd)

        rate.sleep()
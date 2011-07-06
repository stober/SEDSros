#! /usr/bin/env python
"""
Author: Jeremy M. Stober
Program: DS_DRIVER.PY
Date: Monday, June 20 2011
Description: Publishes ds commands to r_cart/command_pose.
"""

import roslib
roslib.load_manifest('tf')
roslib.load_manifest('seds')

import tf
import rospy
import rospy.rostime as rostime
from geometry_msgs.msg import PoseStamped

from seds.srv import DSSrv
from seds.srv import DSLoaded
from std_srvs.srv import Empty

import numpy
import getopt
import sys
npa = numpy.array

import threading

# TODO : add ability to switch to just JTTeleop
# TODO : add the ability to adjust vm/feedback/rate online

class PR2Driver:

    def __init__(self, vm, feedback, source_frameid, target_frameid, rate):

        rospy.loginfo("Initialized with vm: %f and feedback: %s on sf: %s and tf: %s" % (vm, str(feedback), source_frameid, target_frameid))

        self.vm = vm
        self.feedback = feedback
        self.source_frameid = source_frameid
        self.target_frameid = target_frameid
        self.rate = rate

        self.listener = tf.TransformListener()
        self.pub = rospy.Publisher('r_cart/command_pose', PoseStamped)

        # wait for the ds server
        rospy.loginfo('Waiting for ds_node...')
        rospy.wait_for_service('/ds_node/ds_server')
        rospy.loginfo('ds_node found!')

        self.dl = rospy.ServiceProxy('/ds_node/is_loaded', DSLoaded) # check whether the ds_server has a model
        self.ds = rospy.ServiceProxy('/ds_node/ds_server', DSSrv) # the running model

        self.startSRV = rospy.Service('/pr2_driver/start', Empty, self.start)
        self.stopSRV = rospy.Service('/pr2_driver/stop', Empty, self.stop)
        self.quitSRV = rospy.Service('/pr2_driver/quit', Empty, self.quit)

        self.zerot = rostime.Time(0)

        # wait for the proper /tf transforms
        rospy.loginfo('Waiting for transform...')
        tfound = False
        while not tfound:
            try:
                self.listener.waitForTransform(source_frame=source_frameid, target_frame=target_frameid,time=self.zerot,timeout=rostime.Duration(10))
                tfound = True # no exception
            except tf.Exception, error:
                print error
        rospy.loginfo('Transform found!')

        self.cmd = PoseStamped()
        self.cmd.header.frame_id = "/" + source_frameid

        self.running = False
        self.runningCV = threading.Condition()

    def quit(self, ignore):
        """
        Call the quit service to quit the pr2_driver.
        """
        self.runningCV.acquire()
        self.running = False
        rospy.core.signal_shutdown("quit pr2_driver")
        self.runningCV.notify()
        self.runningCV.release()
        return []


    def stop(self, ignore):
        """
        Call the stop service to stop the pr2_driver.
        """
        self.runningCV.acquire()

        self.running = False
        rospy.loginfo("pr2_driver stopping!")

        self.runningCV.notify()
        self.runningCV.release()
        return []

    def start(self, ignore):
        """
        Call the start service to start the pr2_driver.
        """

        self.runningCV.acquire()

        res = self.dl()
        if res.loaded:

            # init some variables
            et = self.listener.lookupTransform(self.source_frameid, self.target_frameid, self.zerot)
            self.x = list(et[0][:])
            self.rot = list(et[1][:])
            self.newx = self.x

            self.running = True
            rospy.loginfo("pr2_driver starting!")
            # need to send a signal to wake up the main thread?
        else:
            rospy.loginfo("ds_node model is not loaded -- not starting!")

        self.runningCV.notify()
        self.runningCV.release()
        return []

    def spin(self):

        rospy.loginfo("Running!")

        try:

            while not rospy.is_shutdown():

                self.runningCV.acquire()
                if self.running:

                    # if feedback is true then re-intialize x,rot on every loop using tf
                    if self.feedback:
                        et = listener.lookupTransform(source_frameid, target_frameid, rostime.Time(0))
                        self.rot = list(et[1][:])
                        self.x = list(et[0][:])
                    else:
                        self.x = self.newx

                    rospy.loginfo("x: %s" % str(self.x))

                    self.dx = list(self.ds(self.x).dx)

                    rospy.loginfo("dx: %s" % str(self.dx))
                    self.newx = list(npa(self.x) + self.vm * npa(self.dx))

                    rospy.loginfo("nx: %s" % str(self.newx))

                    self.cmd.pose.position.x = self.newx[0]
                    self.cmd.pose.position.y = self.newx[1]
                    self.cmd.pose.position.z = self.newx[2]

                    # just use the tf pose orientations
                    self.cmd.pose.orientation.x = self.rot[0]
                    self.cmd.pose.orientation.y = self.rot[1]
                    self.cmd.pose.orientation.z = self.rot[2]
                    self.cmd.pose.orientation.w = self.rot[3]

                    self.pub.publish(self.cmd)
                    self.rate.sleep()

                else:
                    # wait around until a start service call
                    # check for an interrupt every once and awhile
                    self.runningCV.wait(1.0)

                self.runningCV.release()

        except KeyboardInterrupt:
            rospy.logdebug('keyboard interrupt, shutting down')
            rospy.core.signal_shutdown('keyboard interrupt')

def main():

    # rospy gets first crack at sys.argv
    rospy.myargv(argv=sys.argv)
    (options,args) = getopt.getopt(sys.argv[1:], 'v:fs:t:', ['vm=','feedback','source=','target='])

    rospy.init_node('pr2_driver')

    source_frameid = rospy.get_param("/r_cart/root_name/source_frameid","torso_lift_link")
    target_frameid = rospy.get_param("/r_cart/tip_name/target_frameid","r_gripper_tool_frame")
    vm = rospy.get_param("/pr2_driver/velocity_multiplier", 25.0)
    feedback = rospy.get_param("/pr2_driver/feedback", False)

    for o,a in options:
        if o in ('-v','--vm'):
            vm = float(a)
        elif o in ('-f','--feedback'):
            feedback = True
        elif o in ('-s','--source'):
            source_frameid = a
        elif o in ('-t','--target'):
            target_frameid = a

    driver = PR2Driver(vm, feedback, source_frameid, target_frameid, rospy.Rate(100)) # start node
    driver.spin()

if __name__ == '__main__':
    main()
from __future__ import absolute_import

from . import ros_setup

try:
    import roslib
    import rospy
    from rospy.service import ServiceManager
    import rosservice, rostopic
    import actionlib_msgs.msg
except ImportError:
    ros_setup.ROS_emulate_setup()
    import roslib
    import rospy
    from rospy.service import ServiceManager
    import rosservice, rostopic
    import actionlib_msgs.msg

from importlib import import_module
from collections import deque, OrderedDict

from .message_conversion import get_msg, get_msg_dict


def get_topic_msg(topic):
    return get_msg(topic.rostype)


def get_topic_msg_dict(topic):
    return get_msg_dict(topic.rostype)


"""
TopicBack is the class handling conversion from Python to ROS Topic
"""
class TopicBack(object):
    def __init__(self, topic_name, topic_type, allow_pub=True, allow_sub=True, queue_size=1):
        self.name = topic_name
        # getting the fullname to make sure we start with /
        self.fullname = self.name if self.name.startswith('/') else '/' + self.name

        topic_type_module, topic_type_name = tuple(topic_type.split('/'))
        roslib.load_manifest(topic_type_module)
        msg_module = import_module(topic_type_module + '.msg')

        self.rostype_name = topic_type
        self.rostype = getattr(msg_module, topic_type_name)

        self.allow_pub = allow_pub
        self.allow_sub = allow_sub

        self.msgtype = get_topic_msg_dict(self)
        self.msg = deque([], queue_size)

        self.pub = None
        if self.allow_pub:
            self.pub = rospy.Publisher(self.name, self.rostype, queue_size=1)
            # CAREFUL ROS publisher doesnt guarantee messages to be delivered
            # stream-like design spec -> loss is acceptable.
            # TODO : maybe combine with "get_num_connections" to determine if publisher ready to publish or not yet ?

        self.sub = None
        if self.allow_sub:
            self.sub = rospy.Subscriber(self.name, self.rostype, self.topic_callback)

        self.empty_cb = None

    def asdict(self):
        """
        Here we provide a dictionary suitable for a representation of the Topic instance
        the main point here is to make it possible to transfer this to remote processes.
        We are not interested in pickleing the whole class with Subscriber and Publisher
        :return:
        """
        return OrderedDict({
            'name': self.name,
            'fullname': self.fullname,
            'msgtype': self.msgtype,
            'allow_sub': self.allow_sub,
            'allow_pub': self.allow_pub,
            'rostype': self.rostype,
            'rostype_name': self.rostype_name,
        })

    def publish(self, msg):
        # enforcing correct type to make send / receive symmetric and API less magical
        # Doing message conversion visibly in code before sending into the black magic tunnel sounds like a good idea
        if isinstance(msg, self.rostype):
            self.pub.publish(msg)  # This should return False if publisher not fully setup yet
            return True  # because the return spec of rospy's publish is not consistent
        return False

    def get(self, num=0, consume=False):
        if not self.msg:
            return None

        res = None
        #TODO : implement returning multiple messages ( paging/offset like for long REST requests )
        if consume:
            res = self.msg.popleft()
            if 0 == len(self.msg) and self.empty_cb:
                self.empty_cb()
                #TODO : CHECK that we can survive here even if we get dropped from the topic list
        else:
            res = self.msg[0]

        return res

    #returns the number of unread message
    def unread(self):
        return len(self.msg)

    def set_empty_callback(self, cb):
        self.empty_cb = cb

    def topic_callback(self, msg):
        self.msg.appendleft(msg)

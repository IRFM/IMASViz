from threading import Thread

class AbstractCommandThread(Thread):

    def __init__(self, view, nodeData = None, threadingEvent=None):
        Thread.__init__(self)
        self.view = view
        self.nodeData = nodeData
        self.threadingEvent = threadingEvent

    def execute(self):
        self.start()

# import wx
# class ResultEvent(wx.PyEvent):
#   def __init__(self, data, eventID):
#     wx.PyEvent.__init__(self)
#     self.SetEventType(eventID)
#     self.data = data


from PyQt5.QtCore import QEvent

class ResultEvent(QEvent):
    def __init__(self, data, eventID):
        EVENT_TYPE = QEvent.Type(QEvent.registerEventType(eventID))
        #thread-safe
        QEvent.__init__(self, EVENT_TYPE)
        self.data = data
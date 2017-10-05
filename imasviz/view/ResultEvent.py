import wx

class ResultEvent(wx.PyEvent):
  def __init__(self, data, eventID):
    wx.PyEvent.__init__(self)
    self.SetEventType(eventID)
    self.data = data
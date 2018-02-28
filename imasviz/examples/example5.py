#!/usr/bin/python
"""Mouse event handling simple example. Pressing the middle mouse button within
the application frame will display the mouse cursor coordinates.

Sources:
- https://wxpython.org/Phoenix/docs/html/wx.MouseEvent.html
- https://stackoverflow.com/questions/11927178/mouse-events-on-text-in-python-using-wxpython
"""

from imasviz.Browser_API import Browser_API
from imasviz.data_source.DataSourceFactory import DataSourceFactory
from imasviz.util.GlobalValues import GlobalValues
from imasviz.util.GlobalOperations import GlobalOperations
import wx
import os

def GetMousePosition(evt):
    """ Display mouse cursor position (x and y coordinates) upon event.
    """
    x, y = evt.GetPosition()
    print("Current mouse position x = ", x, " y= ", y)


def OnMouseEvent( event):
    """Follows every mouse action occurence (including mouse movement).
    This is stripped down WxDataTreeView routine.
    Note: In this case, right Mouse events somehow work only on 'log' window.
    """

    pos = event.GetPosition()

    if event.LeftDown():
        print('Left Mouse Button Click')

    elif event.RightDown() and not event.ShiftDown():
        print('Right Mouse Button Click')

    elif event.RightDown() and event.ShiftDown():
        print('Right Mouse Button Click + Shift Key Down')

    else:
        event.Skip()

app = wx.App()

GlobalOperations.checkEnvSettings()

api = Browser_API()

dataSourceFactory = DataSourceFactory()

"""Specifying data source"""
f1 = api.CreateDataTree(dataSourceFactory.create(shotNumber=52344,
                                                 runNumber=0,
                                                 userName=os.environ["USER"],
                                                 imasDbName="test"))

# f1 = api.CreateDataTree(dataSourceFactory.create(
#     dataSourceName=GlobalValues.TORE_SUPRA, shotNumber=47977))

"""Bind middle mouse button event handler to application"""
app.Bind(wx.EVT_MIDDLE_UP, GetMousePosition)

"""Bind multiple mouse event handlers (class) to application"""
app.Bind(wx.EVT_MOUSE_EVENTS, OnMouseEvent)

"""Show frame"""
f1.Show(True)

app.MainLoop()
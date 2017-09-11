import wx.py
import os
import sys
from imasviz.data_source.DataSourceFactory import DataSourceFactory
from imasviz.Browser_API import Browser_API
from imasviz.util.GlobalOperations import GlobalOperations
from imasviz.util.GlobalValues import GlobalValues
from imasviz.data_source.IMASDataSource import IMASDataSource


class TabOne(wx.Panel):
    def __init__(self,parent):
        wx.Panel.__init__(self,parent)

        self.dataSource = None

        self.vbox = wx.BoxSizer(wx.VERTICAL)
        hboxRadioButtons = wx.BoxSizer(wx.HORIZONTAL)

        self.gridSizer_native = wx.GridSizer(rows=4, cols=2, hgap=5, vgap=5)
        self.gridSizer_tore_supra = wx.GridSizer(rows=2, cols=2, hgap=5, vgap=5)

        self.rb2 = wx.RadioButton(self, -1, 'Tore Supra')
        self.rb1 = wx.RadioButton(self, -1, 'IMAS local database ')

        self.shotNumberStaticText = wx.StaticText(self, -1, 'Shot number  ')
        self.runNumberStaticText = wx.StaticText(self, -1, 'Run number')

        self.shotNumberStaticTextTS = wx.StaticText(self, -1, 'Shot number  ')
        self.runNumberStaticTextTS = wx.StaticText(self, -1, 'Run number')

        self.userNameStaticText = wx.StaticText(self, -1, 'User name  ')
        self.imasDbNameStaticText = wx.StaticText(self, -1, 'IMAS database name  ')

        self.userName = wx.TextCtrl(self, -1, os.environ["USER"], size=(150, -1))
        self.imasDbName = wx.TextCtrl(self, -1,  size=(150, -1))

        self.shotNumber= wx.TextCtrl(self, -1, size=(150, -1))
        self.runNumber = wx.TextCtrl(self, -1, '0', size=(150, -1))

        self.shotNumberTS = wx.TextCtrl(self, -1, size=(150, -1))
        self.runNumberTS = wx.TextCtrl(self, -1, '0', size=(150, -1))


        button_open = wx.Button(self, 1, 'Open')

        self.logWindow = wx.TextCtrl(self, wx.ID_ANY,"Welcome to the IMAS data browser !\n", size=(500, 100), style = wx.TE_MULTILINE|wx.TE_READONLY|wx.HSCROLL)

        #Radio buttons
        hboxRadioButtons.Add(self.rb1, 1, wx.EXPAND | wx.ALL, 5)
        hboxRadioButtons.Add(self.rb2, 1, wx.EXPAND | wx.ALL, 5)

        self.gridSizer_native.Add(self.userNameStaticText, 0, wx.LEFT, 10)
        self.gridSizer_native.Add(self.userName, 0, wx.LEFT, 10)
        self.gridSizer_native.Add(self.imasDbNameStaticText, 0, wx.LEFT, 10)
        self.gridSizer_native.Add(self.imasDbName, 0, wx.LEFT, 10)
        self.gridSizer_native.Add(self.shotNumberStaticText, 0, wx.LEFT, 10)
        self.gridSizer_native.Add(self.shotNumber, 0, wx.LEFT, 10)
        self.gridSizer_native.Add(self.runNumberStaticText, 0, wx.LEFT, 10)
        self.gridSizer_native.Add(self.runNumber, 0, wx.LEFT, 10)

        self.gridSizer_tore_supra.Add(self.shotNumberStaticTextTS, 0, wx.LEFT, 10)
        self.gridSizer_tore_supra.Add(self.shotNumberTS, 0, wx.LEFT, 10)
        self.gridSizer_tore_supra.Add(self.runNumberStaticTextTS, 0, wx.LEFT, 10)
        self.gridSizer_tore_supra.Add(self.runNumberTS, 0, wx.LEFT, 10)

        self.vbox.Add(hboxRadioButtons, 0, wx.TOP, 10)
        self.vbox.Add(self.gridSizer_native, 0, wx.TOP, 10)
        self.vbox.Add(self.gridSizer_tore_supra, 0, wx.TOP, 10)

        self.vbox.Add(button_open, 0, wx.ALIGN_LEFT | wx.TOP | wx.BOTTOM, 60)
        self.vbox.Add(self.logWindow, 1, wx.ALL|wx.EXPAND, 5)

        self.Bind(wx.EVT_RADIOBUTTON, self.SwitcherNative, id=self.rb1.GetId())
        self.Bind(wx.EVT_RADIOBUTTON, self.SwitcherTS, id=self.rb2.GetId())
        self.Bind(wx.EVT_BUTTON, self.Open, id=1)

        self.SetSizer(self.vbox)

        # handler = WxTextCtrlHandler(log)
        # logger.addHandler(handler)
        # FORMAT = "%(asctime)s %(levelname)s %(message)s"
        # handler.setFormatter((logging.Formatter(FORMAT)))
        # logger.setLevel(logging.DEBUG)
        self.dataSourceName = GlobalValues.IMAS_NATIVE  # default value
        self.rb1.SetValue(True)
        self.shell = None
        self.handlerValue = 0

        from imasviz.view.WxDataTreeView import TextCtrlLogger

        self.log = TextCtrlLogger(self.logWindow)

        self.vbox.Hide(2)
        self.vbox.Show(1)


        # logging
    def CheckInputs(self):

        if self.rb1.GetValue() :

            userName = self.userName.GetValue()
            imasDbName = self.imasDbName.GetValue()
            shotnumbertext = self.shotNumber.GetValue()
            runnumbertext = self.runNumber.GetValue()

            if userName == '':
                raise ValueError("'User name' field is empty.")

            if imasDbName == '':
                raise ValueError("'IMAS database name' field is empty.")

            if shotnumbertext == '' or runnumbertext == '':
                raise ValueError("'Shot number' or 'run number' field is empty.")
        else:
            shotnumbertext = self.shotNumberTS.GetValue()
            runnumbertext =  self.runNumberTS.GetValue()

            if shotnumbertext == '' or runnumbertext == '' :
                raise ValueError("'Shot number' or 'run number' field is empty.")

        GlobalOperations.check(self.dataSourceName, int(shotnumbertext))


    def SwitcherTS(self, evt):
        self.dataSourceName = GlobalValues.TORE_SUPRA
        self.vbox.Hide(1)
        self.vbox.Show(2)
        self.Layout()
        self.runNumberTS.SetValue('0')
        self.runNumberTS.Enable(False)


    def SwitcherNative(self, evt):
        self.dataSourceName = GlobalValues.IMAS_NATIVE
        self.vbox.Hide(2)
        self.vbox.Show(1)
        self.Layout()

    def Open(self, evt):

        try:

            from imasviz.view.HandlerName import HandlerName

            self.CheckInputs()

            apiHandlerName = HandlerName.getAPIHandler(0)
            if  self.handlerValue == 0:
                self.shell.run(apiHandlerName + " = Browser_API()")

            if self.dataSourceName == GlobalValues.IMAS_NATIVE:

                IMASDataSource.try_to_open(self.imasDbName.GetValue(), self.userName.GetValue(), int(self.shotNumber.GetValue()), int(self.runNumber.GetValue()))

                for i in xrange(0, 10):
                    vname = "MDSPLUS_TREE_BASE_" + str(i)
                    mds = os.environ['HOME']  + "/public/imasdb/" + self.imasDbName.GetValue() + "/3/" + str(i)
                    os.environ[vname] = mds


            dataSourceFactoryHandlerName = HandlerName.getDataSourceFactoryHandler(self.handlerValue)
            self.shell.run(dataSourceFactoryHandlerName + " = DataSourceFactory()")

            dataSourceHandlerName = HandlerName.getDataSourceHandler(self.handlerValue)

            if self.rb1.GetValue() :
                self.shell.run(dataSourceHandlerName + " = " + dataSourceFactoryHandlerName + ".create(" + 
                               self.shotNumber.GetValue() + ","  + self.runNumber.GetValue() + ",'" + 
                               self.userName.GetValue() + "','" + self.imasDbName.GetValue() + "','" + self.dataSourceName + "')")
            else:
                self.shell.run(
                    dataSourceHandlerName + " = " + dataSourceFactoryHandlerName + ".create(" + self.shotNumberTS.GetValue() +
                    "," + self.runNumberTS.GetValue() + ",'" + self.dataSourceName + "')")

            viewhandlerName = HandlerName.getWxDataTreeViewHandler(self.handlerValue)
            self.shell.run(viewhandlerName + " = " + apiHandlerName + ".CreateDataTree(" + dataSourceHandlerName + ")")
            self.shell.push(apiHandlerName + ".ShowDataTree(" + viewhandlerName + ")")
            self.shell.push(viewhandlerName + ".Center()")

            self.handlerValue += 1

        except ValueError as e:
            self.log.error(str(e))


class TabTwo(wx.Panel):
    def __init__(self,parent):
        wx.Panel.__init__(self,parent)
        wx.StaticText(self,-1,"Scripting ",(20,20))
        vbox = wx.BoxSizer(wx.VERTICAL)
        self.shell = wx.py.shell.Shell(self, -1)
        vbox.Add(self.shell, 1, wx.EXPAND | wx.TOP | wx.RIGHT | wx.LEFT, 15)
        self.SetSizer(vbox)

class TabThree(wx.Panel):
    def __init__(self,parent):
        wx.Panel.__init__(self,parent)

        self.dataSource = None

        self.vbox = wx.BoxSizer(wx.VERTICAL)

        self.gridSizer_native = wx.GridSizer(rows=4, cols=2, hgap=5, vgap=5)

        self.shotNumberStaticText = wx.StaticText(self, -1, 'Shot number  ')
        self.runNumberStaticText = wx.StaticText(self, -1, 'Run number')
        self.imasDbNameStaticText = wx.StaticText(self, -1, 'IMAS public database name  ')

        self.shotNumber= wx.TextCtrl(self, -1, size=(150, -1))
        self.runNumber = wx.TextCtrl(self, -1, '0', size=(150, -1))
        #self.imasDbName = wx.TextCtrl(self, -1, size=(150, -1))
        publicDatabases = ['WEST']
        self.imasDbName = wx.Choice(self, choices=publicDatabases, style=wx.CB_READONLY)
        self.imasDbName.SetSelection(0)

        button_open = wx.Button(self, 1, 'Open')

        self.logWindow = wx.TextCtrl(self, wx.ID_ANY,"Welcome to the IMAS data browser !\n", size=(500, 100), style = wx.TE_MULTILINE|wx.TE_READONLY|wx.HSCROLL)

        self.gridSizer_native.Add(self.imasDbNameStaticText, 0, wx.LEFT, 10)
        self.gridSizer_native.Add(self.imasDbName, 0, wx.LEFT, 10)
        self.gridSizer_native.Add(self.shotNumberStaticText, 0, wx.LEFT, 10)
        self.gridSizer_native.Add(self.shotNumber, 0, wx.LEFT, 10)
        self.gridSizer_native.Add(self.runNumberStaticText, 0, wx.LEFT, 10)
        self.gridSizer_native.Add(self.runNumber, 0, wx.LEFT, 10)

        self.vbox.Add(self.gridSizer_native, 0, wx.TOP, 10)

        self.vbox.Add(button_open, 0, wx.ALIGN_LEFT | wx.TOP | wx.BOTTOM, 60)
        self.vbox.Add(self.logWindow, 1, wx.ALL|wx.EXPAND, 5)
        self.Bind(wx.EVT_BUTTON, self.OpenPublic, id=1)

        self.SetSizer(self.vbox)

        self.dataSourceName = GlobalValues.IMAS_UDA  # default value
        self.shell = None
        self.handlerValue = 0

        from imasviz.view.WxDataTreeView import TextCtrlLogger

        self.log = TextCtrlLogger(self.logWindow)

        #self.vbox.Hide(2)
        #self.vbox.Show(1)
        self.runNumber.SetEditable(False)

    def OpenPublic(self, evt):

        try:

            from imasviz.view.HandlerName import HandlerName

            self.CheckInputs()

            apiHandlerName = HandlerName.getAPIHandler(0)
            if  self.handlerValue == 0:
                self.shell.run(apiHandlerName + " = Browser_API()")

            #IMASDataSource.try_to_open(self.imasDbName.GetValue(), self.userName.GetValue(), int(self.shotNumber.GetValue()), int(self.runNumber.GetValue()))

            for i in xrange(0, 10):
                vname = "MDSPLUS_TREE_BASE_" + str(i)
                mds = os.environ['HOME']  + "/public/imasdb/" + self.imasDbName.GetString(self.imasDbName.GetSelection()) + "/3/" + str(i)
                os.environ[vname] = mds


            dataSourceFactoryHandlerName = HandlerName.getDataSourceFactoryHandler(self.handlerValue)
            self.shell.run(dataSourceFactoryHandlerName + " = DataSourceFactory()")

            dataSourceHandlerName = HandlerName.getDataSourceHandler(self.handlerValue)

            self.shell.run(dataSourceHandlerName + " = " + dataSourceFactoryHandlerName + ".create(" +
                               self.shotNumber.GetValue() + ","  + self.runNumber.GetValue() + ",'" +
                           self.imasDbName.GetString(self.imasDbName.GetSelection()) + "','" + self.dataSourceName + "')")

            viewhandlerName = HandlerName.getWxDataTreeViewHandler(self.handlerValue)
            self.shell.run(viewhandlerName + " = " + apiHandlerName + ".CreateDataTree(" + dataSourceHandlerName + ")")
            self.shell.push(apiHandlerName + ".ShowDataTree(" + viewhandlerName + ")")
            self.shell.push(viewhandlerName + ".Center()")

            self.handlerValue += 1

        except ValueError as e:
            self.log.error(str(e))


    def CheckInputs(self):

        imasDbName = self.imasDbName.GetString(self.imasDbName.GetSelection())
        shotnumbertext = self.shotNumber.GetValue()
        runnumbertext = self.runNumber.GetValue()

        if imasDbName == '':
            raise ValueError("'IMAS public database name' field is empty.")

        if shotnumbertext == '':
            raise ValueError("'Shot number' field is empty.")

        if runnumbertext == '':
            raise ValueError("'Run number' field is empty.")

        GlobalOperations.check(self.dataSourceName, int(shotnumbertext))



class GUIFrame(wx.Frame):
    def __init__(self,parent,wxid,title):
        wx.Frame.__init__(self,parent,wxid,title, wx.DefaultPosition, (500, 400))
        self.InitUI()
        self.Centre
        self.Show(True)

    def InitUI(self):
        nb = wx.Notebook(self)
        tab1 = TabOne(nb)
        tab2 = TabTwo(nb)
        tab3 = TabThree(nb)
        tab1.shell = tab2.shell
        tab3.shell = tab2.shell
        nb.AddPage(tab1,"Data Source")
        nb.AddPage(tab3, "Public Data Source")
        nb.AddPage(tab2, "Scripting ")
        self.Bind(wx.EVT_CLOSE, self.onClose)

    def onClose(self, event):
        sys.exit(0)

class MyApp(wx.App):

    def OnInit(self):
        GlobalOperations.checkEnvSettings()
        frm = GUIFrame(None, -1, "IMAS_VIZ")
        frm.Centre()
        frm.Show(True)
        return True

if __name__ == "__main__":
    app = MyApp(0)
    app.MainLoop()




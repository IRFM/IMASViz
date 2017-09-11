import wx

class SubPlotsCustomization(wx.Panel):
    def __init__(self, parent, subPlotsList):
        wx.Panel.__init__(self, parent)
        self.stx = None
        self.sty = []
        self.txtCtrl = []
        self.hboxList = []

        self.sty_legends = []
        self.txtCtrl_legends = []
        self.hboxList_legends = [] #legends
        vbox = wx.BoxSizer(wx.VERTICAL)


        self.stx_axis_label = wx.StaticText(self, -1, 'X axis label: ')
        self.hboxList.append(wx.BoxSizer(wx.HORIZONTAL))
        self.hboxList[0].Add(self.stx_axis_label, 0, wx.ALIGN_LEFT | wx.TOP | wx.BOTTOM, 20)
        self.txtCtrl.append(wx.TextCtrl(self, -1, subPlotsList[0].labelX, size=(150, -1)))
        self.hboxList[0].Add(self.txtCtrl[0], 0, wx.ALIGN_LEFT | wx.TOP | wx.BOTTOM, 20)
        vbox.Add(self.hboxList[0], 0, wx.TOP, 10)

        subplots=[]
        for i in range(0, len(subPlotsList)):

            subplot_number = subPlotsList[i].subplot_number
            if (subplot_number not in subplots):
                subplots.append(subplot_number)

                self.sty.append(wx.StaticText(self, -1, 'Y axis label ' + '( subplot ' + str(subplot_number) + ' ): '))
                self.txtCtrl.append(wx.TextCtrl(self, -1, subPlotsList[i].labelY, size=(150, -1)))
                self.hboxList.append(wx.BoxSizer(wx.HORIZONTAL))
                self.hboxList[i+1].Add(self.sty[i], 0, wx.ALIGN_LEFT | wx.TOP | wx.BOTTOM, 20)
                self.hboxList[i+1].Add(self.txtCtrl[i+1], 0, wx.ALIGN_LEFT | wx.TOP | wx.BOTTOM, 20)
                vbox.Add(self.hboxList[i+1], 0, wx.TOP, 10)

        self.stx_legends = wx.StaticText(self, -1, 'Legends: ')
        vbox.Add(self.stx_legends, 0, wx.TOP, 20)


        for i in range(0, len(subPlotsList)):
            self.sty_legends.append(wx.StaticText(self, -1, 'Legend ' + str(i) + ' : '))
            self.txtCtrl_legends.append(wx.TextCtrl(self, -1, subPlotsList[i].legend, size=(150, -1)))
            self.hboxList_legends.append(wx.BoxSizer(wx.HORIZONTAL))
            self.hboxList_legends[i].Add(self.sty_legends[i], 0, wx.ALIGN_LEFT | wx.TOP | wx.BOTTOM, 20)
            self.hboxList_legends[i].Add(self.txtCtrl_legends[i], 0, wx.ALIGN_LEFT | wx.TOP | wx.BOTTOM, 20)
            vbox.Add(self.hboxList_legends[i], 0, wx.TOP, 10)

        self.SetSizer(vbox)
import imas

class IMASTest:

    def __init__(self):
        pass

    def load(self, machineName):
        ids = imas.ids(1, 5, 0, 0)
        ids.open()  # open the database
        ids.equilibrium.get()
        #ids.open_env('LF218007', 'west', '3')
        #ids.antennas.get()
        # ids.open_env('lf218007', 'west', '3')
        from subprocess import call
        # call(["ls", "-l"])

        # ids.magnetics.get()
        #comment_att_2 = ids.magnetics.ids_properties.comment
        #print comment_att_2

if __name__ == "__main__":
    imasTest = IMASTest()
    try:
        imasTest.load("test")
    except:
        print ("Error1")
    print ("Error2")

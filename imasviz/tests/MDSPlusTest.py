import MDSplus
from MDSplus import Connection
import xml.etree.ElementTree as ET
import os

class MDSPlusTest():


    def parseIDSMagnetics(self):
        tree = ET.parse(os.environ['TS_MAPPINGS_DIR'] + '/magnetics.xml')
        root = tree.getroot()
        magnetics = root.find('magnetics')
        return magnetics


    def connect(self):
       conn = Connection('altair.partenaires.cea.fr:8000')
       expr = 'gettsbase(43970, "GBBT2%1")'
       r = conn.get('execute($)', expr).data()
       print (expr)
       print (r)
       expr = 'size(gettsbase(43970, "GBBT2%1"))'
       s = conn.get('execute($)', expr).data()
       expr = 'dim_of(gettsbase(43970, "GBBT2%1"))'
       t = conn.get('execute($)', expr).data()
       print (expr)
       print (t)


if __name__ == "__main__":
    mdsp = MDSPlusTest()
    mdsp.connect()

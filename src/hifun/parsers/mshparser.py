import sys
import re
import unittest
import gzip 

class ZoneItem:

    def __init__(self, zoneid, zonetype, zonename=None, bc=None):
        self.zoneid = zoneid
        self.zonetype = zonetype
        self.zonename = zonename
        self.bc = bc

    def __getitem__(self, name):
        if name=="id":
            return self.zoneid
        elif name=="name":
            return self.zonename
        elif name=="type":
            return self.zonetype
        elif name=="bc":
            return self.bc

    def __setitem__(self, key, value):
        if key=="name":
            self.zonename = value
        elif key=="bc":
            self.bc = value

    def __str__(self):
        return str((self.zonename, self.bc))

    def __repr__(self):
        return self.__str__()


class MeshParser:
            
    def __init__(self, filename):
        self.filename = filename
        self._parseMshFile(filename)

    def fromhex(self, s):
        v = "0123456789abcdef"
        vals = {}
        for i in range(len(v)):
            vals[v[i]] = i
        s = [i for i in s]

        s.reverse()
        sum = 0
        for i in range(len(s)):
            sum = sum + (16**i)*vals[s[i]] 
            
        return int(sum)
    
    def _openFile(self, filename):
        if filename.endswith(".gz"):
            return gzip.GzipFile(filename)
        else:
            return open(filename)
            


    def _parseMshFile(self, filename):
        f = self._openFile(filename)
        comment = re.compile('\(0\s+.*\)')
        zone = re.compile("\(45\s+\((\d+)\s+(\S+)\s+(\S+)\s*\)\(\)\)")
        czone = re.compile("\((1[23])\s*\(([0-9a-f]+)\s+[0-9a-f]+\s[0-9a-f]+\s+([0-9a-f]+)\s+\d\)")
	dimension = re.compile('\(2\s+([23])\)')

        zones = {}
        self.computedZones = {}
        line = f.readline()

        while line:
            m1 = re.match(zone, line)
            m2 = re.match(czone, line)
	    m3 = re.match(dimension,line)
            if m2:
                a, b, c= m2.groups()

                if a == '13':
                    if c == '2':
                        name = "InteriorFaceZone_" 
                    else:
                        name = "BoundaryFaceZone_"
                    self.computedZones[self.fromhex(b)] = ZoneItem(b, a, name + str(self.fromhex(b)))
                elif a == '12':
                    self.computedZones[self.fromhex(b)] = ZoneItem(b,a,"CellZone_"+str(self.fromhex(b)), bc="Fluid")
         
            elif m1:
                a, b, c = m1.groups()
                zones[int(a)]=(b,c)

	    elif m3:
		self.dimension = m3.groups()

            line = f.readline()
        #end while
        f.close()

        for k,v in zones.items():
            self.computedZones[k]['bc'] = v[0]
            self.computedZones[k]['name'] = v[1]


    def getFaceZones(self):
        return [z for z in self.computedZones.values() if z['type']=='13']

    def getCellZones(self):
        return [z for z in self.computedZones.values() if z['type']=='12']        

    def getDimention(self):
	return int(self.dimension[0])


class TestMeshParser(unittest.TestCase):
    
    def testBasic(self):
        p = MeshParser("test.msh")
        zones = p.getFaceZones()
        self.assertEqual(len(zones), 7)
        self.assertTrue([z for z in zones if z['name']=="symmetry_1" and z['bc']=="symmetry"])
        self.assertTrue([z for z in zones if z['name']=="symmetry_2" and z['bc']=="symmetry"])
        self.assertTrue([z for z in zones if z['name']=="wall_1" and z['bc']=="wall"])
        self.assertTrue([z for z in zones if z['name']=="wall_2" and z['bc']=="wall"])
        self.assertTrue([z for z in zones if z['name']=="interface_1" and z['bc']=="interface"])
        self.assertTrue([z for z in zones if z['name']=="interface_2" and z['bc']=="interface"])
        self.assertTrue([z for z in zones if z['name']=="default-interior" and z['bc']=="interior"])

    def testComputedZones(self):
        p = MeshParser("test1.msh.gz")
        zones = p.getFaceZones()
        self.assertEqual(len(zones), 7)

    def testFromhex(self):
        p = MeshParser("test1.msh.gz")
        self.assertEqual(p.fromhex('a'),10)
        self.assertEqual(p.fromhex('b'),11)
        self.assertEqual(p.fromhex('c'),12)
        self.assertEqual(p.fromhex('d'),13)
        self.assertEqual(p.fromhex('7b'), 123)
        self.assertEqual(p.fromhex('cb5601d'),213213213)
                         

if __name__=="__main__":
    unittest.main()

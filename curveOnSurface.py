from __future__ import division # allows floating point division from integers
import FreeCAD
import Part
from FreeCAD import Base



#Find the minimum distance to another shape.
#distToShape(Shape s):  Returns a list of minimum distance and solution point pairs.
#
#Returned is a tuple of three: (dist, vectors, infos).
#
#dist is the minimum distance, in mm (float value).
#
#vectors is a list of pairs of App.Vector. Each pair corresponds to solution.
#Example: [(Vector (2.0, -1.0, 2.0), Vector (2.0, 0.0, 2.0)), (Vector (2.0,
#-1.0, 2.0), Vector (2.0, -1.0, 3.0))] First vector is a point on self, second
#vector is a point on s.
#
#infos contains additional info on the solutions. It is a list of tuples:
#(topo1, index1, params1, topo2, index2, params2)
#
#    topo1, topo2 are strings identifying type of BREP element: 'Vertex',
#    'Edge', or 'Face'.
#
#    index1, index2 are indexes of the elements (zero-based).
#
#    params1, params2 are parameters of internal space of the elements. For
#    vertices, params is None. For edges, params is one float, u. For faces,
#    params is a tuple (u,v). 



class curveOnSurface:
    
    def __init__(self, edge = None, face = None):
        self.face = face
        self.edge = edge
        self.curve2D = None
        self.edgeOnFace = None
        self.validate()
        self.reverseTangent  = False
        self.reverseNormal   = False
        self.reverseBinormal = False
        self.validate()

    def setEdge(self, edge):
        self.edge = edge
        self.validate()

    def setFace(self, face):
        self.face = face
        self.validate()

    #def edgeOnFace(self):
        #if self.validate():
            #return( self.curve2D[0].toShape(self.face, self.curve2D[1], self.curve2D[2]))

    def validate(self):
        if (not self.edge == None) and (not self.face == None):
            self.curve2D = self.face.curveOnSurface(self.edge)
            #self.edgeOnFace = self.curve2D[0].toShape(self.face, self.curve2D[1], self.curve2D[2])
            if not isinstance(self.curve2D,tuple):
                newedge = self.face.project([self.edge]).Edges[0]
                self.curve2D = self.face.curveOnSurface(newedge)
                #self.edgeOnFace = self.curve2D[0].toShape(self.face, self.curve2D[1], self.curve2D[2])
            if isinstance(self.curve2D,tuple):
                self.edgeOnFace = self.curve2D[0].toShape(self.face, self.curve2D[1], self.curve2D[2])
                return(True)
            else:
                return(False)
        else:
            return(False)

    def valueAt(self, t):
        if self.edgeOnFace:
            return(self.edgeOnFace.valueAt(t))
        else:
            return(None)

    def tangentAt(self, t):
        if self.edgeOnFace:
            if self.reverseTangent:
                return(self.edgeOnFace.tangentAt(t).negative().normalize())
            else:
                return(self.edgeOnFace.tangentAt(t).normalize())
        else:
            return(None)

    def normalAt(self, t):
        if self.edgeOnFace:
            vec = None
            if self.face:
                if self.curve2D:
                    #print("%s at %f"%(str(self.curve2D[0]),t))
                    p = self.curve2D[0].value(t)
                    #print("%d - %d"%(p.x,p.y))
                    vec = self.face.normalAt(p.x,p.y)
                else:
                    # TODO Try to get self.face normal using distToShape
                    # v = Part.Vertex(self.edge.valueAt(t))
                    # d, pts, info = v.distToShape(self.face)
                    # if info[0]:
                    pass
            else:
                vec = self.edgeOnFace.normalAt(t)
            if self.reverseNormal:
                return(vec.negative().normalize())
            else:
                return(vec.normalize())
        else:
            return(None)

    def binormalAt(self, t):
        ta = self.tangentAt(t)
        n = self.normalAt(t)
        if (not ta == None) and (not n == None):
            if self.reverseBinormal:
                return(ta.cross(n).negative().normalize())
            else:
                return(ta.cross(n).normalize())
        else:
            return(None)



     
from __future__ import division # allows floating point division from integers
import FreeCAD, Part, math
import os, dummy, FreeCADGui
from FreeCAD import Base
from pivy import coin

path_curvesWB = os.path.dirname(dummy.__file__)
path_curvesWB_icons =  os.path.join( path_curvesWB, 'Resources', 'icons')

class makeSpline:
    def __init__(self, obj , edge):
        ''' Add the properties '''
        FreeCAD.Console.PrintMessage("\nDiscretization class Init\n")
        #obj.addProperty("App::PropertyLinkSub",      "Edge",      "Poles",   "Edge").Edge = edge
        obj.addProperty("App::PropertyIntegerConstraint",      "Degree", "General",   "Degree")
        obj.addProperty("App::PropertyInteger",      "Pole", "Poles",   "Pole number").Pole = 1
        obj.addProperty("App::PropertyFloat",        "X",    "Poles",   "X coordinate of the selected pole").X=0.0
        obj.addProperty("App::PropertyFloat",        "Y",    "Poles",   "Y coordinate of the selected pole").Y=0.0
        obj.addProperty("App::PropertyFloat",        "Z",    "Poles",   "Z coordinate of the selected pole").Z=0.0
        obj.addProperty("App::PropertyFloatConstraint",        "W",    "Poles",   "Weight of the selected pole")
        #obj.addProperty("App::PropertyFloat",        "ParameterLast",      "Poles",   "End parameter").ParameterLast=1.0
        #obj.addProperty("App::PropertyVectorList",   "Points",    "Poles",   "Points")
        obj.addProperty("Part::PropertyPartShape",   "Shape",     "Poles",   "Shape")
        obj.Proxy = self
        #obj.Samples = (20,2,1000,10)
        #obj.Points = []
        self.curve = edge.Curve.copy()
        #obj.Pole = (1,1,self.curve.NbPoles,1)
        obj.Degree = (self.curve.Degree,1,8,1)
        obj.W = (1.0,0.0001,1000.0,0.1)
        #self.setEdge(obj)
        self.execute(obj)

        
    #def selectedEdgesToProperty(self, obj, edge):
        #objs = []
        #for o in edge:
            #if isinstance(o,tuple) or isinstance(o,list):
                #if o[0].Name != obj.Name:
                    #objs.append(tuple(o))
            #else:
                #for el in o.SubElementNames:
                    #if "Edge" in el:
                        #if o.Object.Name != obj.Name:
                            #objs.append((o.Object,el))
        #if objs:
            #obj.Edge = objs
            #FreeCAD.Console.PrintMessage(str(edge) + "\n")
            #FreeCAD.Console.PrintMessage(str(obj.Edge) + "\n")


    #def setEdge( self, obj):
        #o = obj.Edge[0]
        #e = obj.Edge[1][0]
        #n = eval(e.lstrip('Edge'))
        #self.edge = o.Shape.Edges[n-1]
        #obj.ParameterFirst = self.edge.FirstParameter
        #obj.ParameterLast = self.edge.LastParameter

    #def buildPoints(self, obj):
        #if   obj.AMethod == "Number":
            #obj.Points = self.edge.discretize( Number = obj.Number,         First = obj.ParameterFirst, Last = obj.ParameterLast)
        #elif obj.AMethod == "Distance":
            #obj.Points = self.edge.discretize( Distance = obj.Distance,     First = obj.ParameterFirst, Last = obj.ParameterLast)
        #elif obj.AMethod == "Deflection":
            #obj.Points = self.edge.discretize( Deflection = obj.Deflection, First = obj.ParameterFirst, Last = obj.ParameterLast)
        #FreeCAD.Console.PrintMessage(str(len(obj.CombPoints))+" Comb points\n")   #+str(obj.CombPoints)+"\n\n")

    def execute(self, obj):
        FreeCAD.Console.PrintMessage("\n* Spline : execute *\n")
        #self.setEdge( obj)
        #self.buildPoints( obj)
        obj.Shape = self.curve.toShape()

    def onChanged(self, fp, prop):
        if (prop == "Degree"):
            if fp.Degree > self.curve.Degree:
                if isinstance(self.curve,Part.BezierCurve):
                    self.curve.increase(fp.Degree)
                elif isinstance(self.curve,Part.BSplineCurve):
                    self.curve.increaseDegree(fp.Degree)
            elif fp.Degree < self.curve.Degree:
                pts = self.curve.discretize(Number = 100)
                bscurve = Part.BSplineCurve() #self.curve.approximateBSpline(0.1,12,fp.Degree,'C2')
                bscurve.approximate(Points = pts, DegMin = fp.Degree, DegMax = fp.Degree, Tolerance = 0.1)
                self.curve = bscurve
                fp.Degree = self.curve.Degree
            #fp.Pole = (1,1,self.curve.NbPoles,1)
            FreeCAD.Console.PrintMessage("Spline : Degree changed\n")
        if prop == "Pole":
            if fp.Pole < 1:
                fp.Pole = 1
            elif fp.Pole > len(self.curve.getPoles()):
                fp.Pole = len(self.curve.getPoles())
            v = self.curve.getPole(fp.Pole)
            w = self.curve.getWeight(fp.Pole)
            fp.X = v.x
            fp.Y = v.y
            fp.Z = v.z
            fp.W = w
            fp.touch()
            FreeCAD.Console.PrintMessage("Spline : Pole changed to "+str(fp.Pole)+"\n")
        if (prop == "X") | (prop == "Y") | (prop == "Z"):
            v = FreeCAD.Vector(fp.X,fp.Y,fp.Z)
            self.curve.setPole(fp.Pole,v)
            FreeCAD.Console.PrintMessage("Spline : Coordinate changed\n")
        if (prop == "W"):
            #v = FreeCAD.Vector(fp.X,fp.Y,fp.Z)
            self.curve.setWeight(fp.Pole,fp.W)
            FreeCAD.Console.PrintMessage("Spline : Coordinate changed\n")
            
    def __getstate__(self):
        return None

    def __setstate__(self,state):
        return None





class editableSpline:
    def parseSel(self, selectionObject):
        res = []
        for obj in selectionObject:
            if obj.HasSubObjects:
                subobj = obj.SubObjects[0]
                if issubclass(type(subobj),Part.Edge):
                    res=subobj
            else:
                res=obj.Object.Shape.Edges[0]
        return res

    def Activated(self):
        s = FreeCADGui.Selection.getSelectionEx()
        edges = self.parseSel(s)

        obj=FreeCAD.ActiveDocument.addObject("Part::FeaturePython","Spline") #add object to document
        makeSpline(obj,edges)
        obj.ViewObject.Proxy = 0
        obj.ViewObject.PointSize = 4.00000
        #obj.ViewObject.ControlPoints = True
        #ViewProviderDiscretization(obj.ViewObject)
        FreeCAD.ActiveDocument.recompute()
            
    def GetResources(self):
        return {'Pixmap' : path_curvesWB_icons+'/editableSpline.svg', 'MenuText': 'editableSpline', 'ToolTip': 'Creates an editable spline from selected edges'}

FreeCADGui.addCommand('editableSpline', editableSpline())



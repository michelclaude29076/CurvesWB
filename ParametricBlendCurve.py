from __future__ import division # allows floating point division from integers
import FreeCAD, Part, math
import os, dummy, FreeCADGui
from FreeCAD import Base
from pivy import coin
import BlendCurve
import CoinNodes

path_curvesWB = os.path.dirname(dummy.__file__)
path_curvesWB_icons =  os.path.join( path_curvesWB, 'Resources', 'icons')

class BlendCurveFP:
    def __init__(self, obj , edges):
        ''' Add the properties '''
        FreeCAD.Console.PrintMessage("\nBlendCurve class Init\n")
        
        obj.addProperty("App::PropertyLinkSub",         "Edge1",      "BlendCurve", "Edge 1").Edge1 = edges[0]
        obj.addProperty("App::PropertyLinkSub",         "Edge2",      "BlendCurve", "Edge 2").Edge2 = edges[1]
        
        obj.addProperty("App::PropertyFloatConstraint", "Parameter1", "BlendCurve", "Location of blend curve")
        obj.addProperty("App::PropertyFloatConstraint", "Scale1",     "BlendCurve", "Scale of blend curve")
        obj.addProperty("App::PropertyEnumeration",     "Continuity1","BlendCurve", "Continuity").Continuity1=["C0","G1","G2"]
        
        obj.addProperty("App::PropertyFloatConstraint", "Parameter2", "BlendCurve", "Location of blend curve")
        obj.addProperty("App::PropertyFloatConstraint", "Scale2",     "BlendCurve", "Scale of blend curve")
        obj.addProperty("App::PropertyEnumeration",     "Continuity2","BlendCurve", "Continuity").Continuity2=["C0","G1","G2"]
        
        obj.addProperty("App::PropertyVectorList",      "CurvePts",   "BlendCurve", "CurvePts")

        obj.Scale1 = (1.,-5.0,5.0,0.1)
        obj.Scale2 = (1.,-5.0,5.0,0.1)
        obj.Parameter1 = ( 1.0, 0.0, 1.0, 0.05 )
        obj.Parameter2 = ( 1.0, 0.0, 1.0, 0.05 )
        obj.Proxy = self

    def initEdges(self, fp):
        n1 = eval(fp.Edge1[1][0].lstrip('Edge'))
        e1 = fp.Edge1[0].Shape.Edges[n1-1]
        n2 = eval(fp.Edge2[1][0].lstrip('Edge'))
        e2 = fp.Edge2[0].Shape.Edges[n2-1]
        return(e1,e2)

    def execute(self, fp):

        e1,e2 = self.initEdges(fp)
        bc = BlendCurve.blendCurve(e1,e2)

        bc.param1 = e1.FirstParameter + fp.Parameter1 * (e1.LastParameter - e1.FirstParameter)
        bc.param2 = e2.FirstParameter + fp.Parameter2 * (e2.LastParameter - e2.FirstParameter)
        bc.cont1 = self.getContinuity(fp.Continuity1)
        bc.cont2 = self.getContinuity(fp.Continuity2)
        bc.scale1 = fp.Scale1
        bc.scale2 = fp.Scale2
        
        fp.Shape = bc.shape()
        fp.CurvePts = bc.getPoles()

    def onChanged(self, fp, prop):
        #print("%s - %s changed"%(fp,prop))
        if prop == "Parameter1":
            if fp.Parameter1 < 0:
                fp.Parameter1 = 0
            elif fp.Parameter1 > 1:
                fp.Parameter1 = 1
        elif prop == "Parameter2":
            if fp.Parameter2 < 0:
                fp.Parameter2 = 0
            elif fp.Parameter2 > 1:
                fp.Parameter2 = 1
        elif prop == "Scale1":
            if fp.Scale1 == 0:
                fp.Scale1 = 0.0001
        elif prop == "Scale2":
            if fp.Scale2 == 0:
                fp.Scale2 = 0.0001

    def getContinuity(self, cont):
        if cont == "C0":
            return 0
        elif cont == "G1":
            return 1
        else:
            return 2


class BlendCurveVP:
    def __init__(self, obj ):
        ''' Add the properties '''
        print("VP init")
        obj.Proxy = self
        self.build()

    def build(self):
        self.active = False
        self.sg = FreeCADGui.ActiveDocument.ActiveView.getSceneGraph()
        self.switch = coin.SoSwitch()
        self.switch.setName("%s_ControlPoints"%self.Object.Name)
        self.empty = coin.SoSeparator() # Empty node
        self.node = coin.SoSeparator()
        self.coord = CoinNodes.coordinate3Node()
        self.poly = CoinNodes.polygonNode((0.5,0.5,0.5),1)
        self.marker = CoinNodes.markerSetNode((1,0,0),coin.SoMarkerSet.DIAMOND_FILLED_7_7)
        self.node.addChild(self.coord)
        self.node.addChild(self.poly)
        self.node.addChild(self.marker)
        self.switch.addChild(self.empty)
        self.switch.addChild(self.node)
        self.sg.addChild(self.switch)

    def attach(self, vobj):
        print("VP attach")
        self.ViewObject = vobj
        self.Object = vobj.Object

    def updateData(self, fp, prop):
        print("%s - %s data update"%(fp,prop))
        if prop == "CurvePts":
            if hasattr(self,'coord') and hasattr(self,'poly'):
                self.coord.points = fp.CurvePts
                self.poly.vertices = self.coord.points

    #def getDisplayModes(self,obj):
         #"Return a list of display modes."
         #modes=[]
         ##modes.append("Curve")
         #modes.append("Poles")
         #return modes

    #def getDefaultDisplayMode(self):
         #'''Return the name of the default display mode. It must be defined in getDisplayModes.'''
         #return "Wireframe"

    #def setDisplayMode(self,mode):
         #return mode

    #def onChanged(self, fp, prop):
        #'''Here we can do something when a single property got changed'''
        #print("%s - %s changed"%(fp,prop))
        #if prop == "CurvePts":
            #if hasattr(self,'coord') and hasattr(self,'poly'):
                #self.coord.points = fp.CurvePts
                #self.poly.vertices = self.coord.points

    def doubleClicked(self,vobj):
        if not hasattr(self,'active'):
            self.active = False
        if not self.active:
            self.active = True
            self.switch.whichChild = 1
        else:
            self.active = False
            self.switch.whichChild = 0
        return True

    def setEdit(self,vobj,mode):   # --- in ViewProvider ---
        print("Start Edit")
        return True

    def unsetEdit(self,vobj,mode):
        print("End Edit")
        return True

    def getIcon(self):
        return (path_curvesWB_icons+'/blend.svg')

    def __getstate__(self):
        return None

    def __setstate__(self,state):
        print("setstate")
        #self.__init__()
        self.build()
        return None



class ParametricBlendCurve:
    def getParam(self, selectionObject):
        param = []
        for o in selectionObject:
            for i in range(len(o.SubObjects)):
                so = o.SubObjects[i]
                p = o.PickedPoints[i]
                poe = so.distToShape(Part.Vertex(p))
                par = poe[2][0][2]
                goodpar = (par - so.FirstParameter) * 1.0 / (so.LastParameter - so.FirstParameter)
                param.append(goodpar)
        return param

    def parseSel(self, selectionObject):
        res = []
        params = []
        for obj in selectionObject:
            if obj.HasSubObjects:
                i = 0
                for subobj in obj.SubObjects:
                    if issubclass(type(subobj),Part.Edge):
                        res.append([obj.Object,obj.SubElementNames[i]])
                    i += 1
            else:
                i = 0
                for e in obj.Object.Shape.Edges:
                    n = "Edge"+str(i)
                    res.append([obj.Object,n])
                    i += 1
        return res
    
    def Activated(self):
        s = FreeCADGui.Selection.getSelectionEx()
        edges = self.parseSel(s)
        print str(edges)
        obj=FreeCAD.ActiveDocument.addObject("Part::FeaturePython","Blend Curve") #add object to document
        BlendCurveFP(obj,edges[0:2])
        BlendCurveVP(obj.ViewObject)
        param = self.getParam(s)
        obj.Parameter1 = param[0]
        obj.Parameter2 = param[1]
        obj.Continuity1 = "G1"
        obj.Continuity2 = "G1"
        FreeCAD.ActiveDocument.recompute()
            
    def GetResources(self):
        return {'Pixmap' : path_curvesWB_icons+'/blend.svg', 'MenuText': 'ParametricBlendCurve', 'ToolTip': 'Creates a parametric blend curve'}

FreeCADGui.addCommand('ParametricBlendCurve', ParametricBlendCurve())




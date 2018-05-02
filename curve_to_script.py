import FreeCADGui
import Part

def curve_to_script(i,c):
    com = ["import FreeCAD",
           "from FreeCAD import Vector",
           "import Part",""]
    if isinstance(c,Part.BSplineCurve):
        com.append("poles%d = %r"%(i,c.getPoles()))
        com.append("weights%d = %r"%(i,c.getWeights()))
        com.append("knots%d = %r"%(i,c.getKnots()))
        com.append("mults%d = %r"%(i,c.getMultiplicities()))
        com.append("periodic%d = %r"%(i,c.isPeriodic()))
        com.append("degree%d = %s"%(i,c.Degree))
        com.append("rational%d = %r"%(i,c.isRational()))
        com.append("bs%d = Part.BSplineCurve()"%i)
        com.append("bs%d.buildFromPolesMultsKnots(poles%d, mults%d, knots%d, periodic%d, degree%d)"%(i,i,i,i,i,i))
        #com.append("bs%d.buildFromPolesMultsKnots(poles%d, mults%d, knots%d, periodic%d, degree%d, weights%d, rational%d)"%(i,i,i,i,i,i,i,i))
        com.append('obj%d = FreeCAD.ActiveDocument.addObject("Part::Spline","BSplineCurve%d")'%(i,i))
        com.append('obj%d.Shape = bs%d.toShape()'%(i,i))
    elif isinstance(c,Part.BezierCurve):
        com.append("poles%d = %r"%(i,c.getPoles()))
        #com.append("degree%d = %s"%(i,c.Degree))
        com.append("be%d = Part.BezierCurve()"%i)
        com.append("be%d.increase(%s)"%(i,c.Degree))
        com.append("be%d.setPoles(poles%d)"%(i,i))
        if c.isRational():
            w = c.getWeights()
            for j in range(len(w)):
                com.append("be%d.setWeight(%i,%f)"%(i,j+1,w[j]))
        com.append('obj%d = FreeCAD.ActiveDocument.addObject("Part::Spline","BezierCurve%d")'%(i,i))
        com.append('obj%d.Shape = be%d.toShape()'%(i,i))
    com.append("")
    
    for s in com:
        FreeCADGui.doCommand(s)

s = FreeCADGui.Selection.getSelectionEx()
i = 0
for so in s:
    for sso in so.SubObjects:
        if hasattr(sso,"Curve"):
            c = sso.Curve
            curve_to_script(i,c)
            i += 1


















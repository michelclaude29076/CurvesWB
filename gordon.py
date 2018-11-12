# This file is a python port of the following files :
#
# /src/geometry/CTiglGordonSurfaceBuilder.cpp
# /src/geometry/CTiglInterpolateCurveNetwork.cpp
#
# from the Tigl library : https://github.com/DLR-SC/tigl under Apache-2 license



#InterpolateCurveNetwork(profile_curves, guide_curves, tol3, tol2)
        #make_curves_compatible
                #parametrize curves to 0:1
                #compute intersection parameters
                #sort_curves (curve_network_sorter)
                #compute average newParameters (intersectionParamsU, intersectionParamsV) (bsa.reparametrizeBSplineContinuouslyApprox)
        #GordonSurfaceBuilder(self.profiles, self.guides, self.intersectionParamsU, self.intersectionParamsV, self.tolerance, self.par_tolerance)
                #surface_gordon()
                        #create_gordon_surface(self.profiles, self.guides, self.intersectionParamsU, self.intersectionParamsV)
                                #check_curve_network_compatibility(profiles, guides, intersection_params_spline_u, intersection_params_spline_v, self.tolerance)
                                #S1 and S2 (bsa.curvesToSurface)
                                #S3 (bsa.pointsToSurface)
                                #increase degree
                                #createCommonKnotsVectorSurface
                                #S1 + S2 - S3 -> self.gordonSurf




import FreeCAD
import Part
from math import pi
from BSplineAlgorithms import BSplineAlgorithms

def debug(o):
    if isinstance(o,Part.BSplineCurve):
        FreeCAD.Console.PrintWarning("\nBSplineCurve\n")
        FreeCAD.Console.PrintWarning("Degree: %d\n"%(o.Degree))
        FreeCAD.Console.PrintWarning("NbPoles: %d\n"%(o.NbPoles))
        FreeCAD.Console.PrintWarning("Knots: %d (%0.2f - %0.2f)\n"%(o.NbKnots, o.FirstParameter, o.LastParameter))
        FreeCAD.Console.PrintWarning("Mults: %s\n"%(o.getMultiplicities()))
        FreeCAD.Console.PrintWarning("Periodic: %s\n"%(o.isPeriodic()))
    elif isinstance(o,Part.BSplineSurface):
        FreeCAD.Console.PrintWarning("\nBSplineSurface\n************\n")
        try:
            u = o.uIso(o.UKnotSequence[0])
            debug(u)
        except Part.OCCError:
            FreeCAD.Console.PrintError("Failed to compute uIso curve\n")
        try:
            v = o.vIso(o.VKnotSequence[0])
            debug(v)
        except Part.OCCError:
            FreeCAD.Console.PrintError("Failed to compute vIso curve\n")
        FreeCAD.Console.PrintWarning("************\n")
    else:
        FreeCAD.Console.PrintMessage("%s\n"%o)


def find(val, array, tol=1e-5):
    for i in range(len(array)):
        if abs(val-array[i]) < tol:
            return(int(i))
    return(-1)

def insertKnot(knot, count, degree, knots, mults, tol = 1e-5):
    if (knot < knots[0] or knot > knots[-1]):
        raise RuntimeError("knot out of range")

    # pos = std::find_if(knots.begin(), knots.end(), helper_function_find(knot, tol)) - knots.begin();
    pos = find(knot, knots, tol)

    if (pos == -1):
        # knot not found, insert new one
        pos = 0;
        while (knots[pos] < knot):
            pos += 1
        knots.insert(pos, knot)
        mults.insert(pos, min(count, degree))
    else:
        # knot found, increase multiplicity
        mults[pos] = min(mults[pos] + count, degree)
        

class GordonSurfaceBuilder(object):
    """Build a Gordon surface from a network of curves"""
    def __init__(self, profiles, guides, params_u, params_v, tol=1e-5, par_tol=1e-7):
        debug("-- GordonSurfaceBuilder initialisation")
        debug("%d profiles and %d guides"%(len(profiles),len(guides)))
        debug(params_u)
        debug(params_v)
        if (len(profiles) < 2) or (len(guides) < 2):
            self.error("Not enough guides or profiles")
        else:
            self.profiles = profiles
            self.guides = guides
        self.intersectionParamsU = params_u
        self.intersectionParamsV = params_v
        self.has_performed = False
        if tol > 0.0:
            self.tolerance = tol
        if par_tol > 0.0:
            self.par_tol = par_tol
    def error(self,mes):
        print(mes)
    def perform(self):
        if self.has_performed:
            return()
        self.create_gordon_surface(self.profiles, self.guides, self.intersectionParamsU, self.intersectionParamsV)
        self.has_performed = True
    def surface_gordon(self):
        self.perform()
        return(self.gordonSurf)
    def surface_profiles(self):
        self.perform()
        return(self.skinningSurfProfiles)
    def surface_guides(self):
        self.perform()
        return(self.skinningSurfGuides)
    def surface_intersections(self):
        self.perform()
        return(self.tensorProdSurf)
    def create_gordon_surface(self, profiles, guides, intersection_params_spline_u, intersection_params_spline_v):
        # check whether there are any u-directional and v-directional B-splines in the vectors
        if len(profiles) < 2:
            self.error("There must be at least two profiles for the gordon surface.")
        if len(guides)  < 2:
            self.error("There must be at least two guides for the gordon surface.")
        # check B-spline parametrization is equal among all curves
        umin = profiles[0].FirstParameter
        umax = profiles[0].LastParameter
        # TODO
        #for (CurveArray::const_iterator it = m_profiles.begin(); it != m_profiles.end(); ++it) {
            #assertRange(*it, umin, umax, 1e-5);

        vmin = guides[0].FirstParameter
        vmax = guides[0].LastParameter
        # TODO
        #for (CurveArray::const_iterator it = m_guides.begin(); it != m_guides.end(); ++it) {
            #assertRange(*it, vmin, vmax, 1e-5);

        # TODO: Do we really need to check compatibility?
        # We don't need to do this, if the curves were reparametrized before
        # In this case, they might be even incompatible, as the curves have been approximated
        self.check_curve_network_compatibility(profiles, guides, intersection_params_spline_u, intersection_params_spline_v, self.tolerance)

        # setting everything up for creating Tensor Product Surface by interpolating intersection points of profiles and guides with B-Spline surface
        # find the intersection points:
        intersection_pnts = [[0]*len(intersection_params_spline_v) for i in range(len(intersection_params_spline_u))]
        #TColgp_Array2OfPnt intersection_pnts(1, static_cast<Standard_Integer>(intersection_params_spline_u.size()),
                                           # 1, static_cast<Standard_Integer>(intersection_params_spline_v.size()));

        # use splines in u-direction to get intersection points
        for spline_idx in range(len(profiles)): #(size_t spline_idx = 0; spline_idx < profiles.size(); ++spline_idx) {
            for intersection_idx in range(len(intersection_params_spline_u)): #(size_t intersection_idx = 0; intersection_idx < intersection_params_spline_u.size(); ++intersection_idx) {
                spline_u = self.profiles[spline_idx]
                parameter = intersection_params_spline_u[intersection_idx]
                intersection_pnts[intersection_idx][spline_idx] = spline_u.value(parameter)

        # check, whether to build a closed continuous surface
        bsa = BSplineAlgorithms(self.par_tol)
        curve_u_tolerance = bsa.REL_TOL_CLOSED * bsa.scale(guides)
        curve_v_tolerance = bsa.REL_TOL_CLOSED * bsa.scale(profiles)
        tp_tolerance      = bsa.REL_TOL_CLOSED * bsa.scale_pt_array(intersection_pnts)
                                                                                    # TODO No IsEqual in FreeCAD
        makeUClosed = False #bsa.isUDirClosed(intersection_pnts, tp_tolerance)# and guides[0].toShape().isPartner(guides[-1].toShape()) #.isEqual(guides[-1], curve_u_tolerance);
        makeVClosed = False #bsa.isVDirClosed(intersection_pnts, tp_tolerance)# and profiles[0].toShape().IsPartner(profiles[-1].toShape())

        # Skinning in v-direction with u directional B-Splines
        debug("-   Skinning profiles")
        surfProfiles = bsa.curvesToSurface(profiles, intersection_params_spline_v, makeVClosed)
        debug(surfProfiles)
        # therefore reparametrization before this method

        # Skinning in u-direction with v directional B-Splines
        debug("-   Skinning guides")
        surfGuides = bsa.curvesToSurface(guides, intersection_params_spline_u, makeUClosed)
        debug(surfGuides)

        # flipping of the surface in v-direction; flipping is redundant here, therefore the next line is a comment!
        surfGuides = bsa.flipSurface(surfGuides)

        # if there are too little points for degree in u-direction = 3 and degree in v-direction=3 creating an interpolation B-spline surface isn't possible in Open CASCADE

        # Open CASCADE doesn't have a B-spline surface interpolation method where one can give the u- and v-directional parameters as arguments
        tensorProdSurf = bsa.pointsToSurface(intersection_pnts, intersection_params_spline_u, intersection_params_spline_v, makeUClosed, makeVClosed)
        debug(tensorProdSurf)

        # match degree of all three surfaces
        degreeU = max(max(surfGuides.UDegree, surfProfiles.UDegree), tensorProdSurf.UDegree)
        degreeV = max(max(surfGuides.VDegree, surfProfiles.VDegree), tensorProdSurf.VDegree)

        # check whether degree elevation is necessary (does method elevate_degree_u()) and if yes, elevate degree
        surfGuides.increaseDegree(degreeU, degreeV)
        surfProfiles.increaseDegree(degreeU, degreeV)
        tensorProdSurf.increaseDegree(degreeU, degreeV)
        print("** Matching to degree %dx%d**"%(degreeU, degreeV))
        print("surfProfiles : %d x %d"%(surfProfiles.NbUPoles, surfProfiles.NbVPoles))
        print("surfGuides : %d x %d"%(surfGuides.NbUPoles, surfGuides.NbVPoles))
        print("tensorProdSurf : %d x %d"%(tensorProdSurf.NbUPoles, tensorProdSurf.NbVPoles))

        surfaces_vector_unmod = [surfGuides, surfProfiles, tensorProdSurf]

        # create common knot vector for all three surfaces
        surfaces_vector = bsa.createCommonKnotsVectorSurface(surfaces_vector_unmod, self.par_tol)

        assert(len(surfaces_vector) == 3)

        self.skinningSurfGuides = surfaces_vector[0]
        self.skinningSurfProfiles = surfaces_vector[1]
        self.tensorProdSurf = surfaces_vector[2]

        print("After createCommonKnotsVectorSurface L1234")
        print("skinningSurfGuides : %d x %d"%(self.skinningSurfGuides.NbUPoles, self.skinningSurfGuides.NbVPoles))
        print("skinningSurfProfiles : %d x %d"%(self.skinningSurfProfiles.NbUPoles, self.skinningSurfProfiles.NbVPoles))
        print("tensorProdSurf : %d x %d"%(self.tensorProdSurf.NbUPoles, self.tensorProdSurf.NbVPoles))

        assert(self.skinningSurfGuides.NbUPoles == self.skinningSurfProfiles.NbUPoles and self.skinningSurfProfiles.NbUPoles == self.tensorProdSurf.NbUPoles)
        assert(self.skinningSurfGuides.NbVPoles == self.skinningSurfProfiles.NbVPoles and self.skinningSurfProfiles.NbVPoles == self.tensorProdSurf.NbVPoles)

        self.gordonSurf = self.skinningSurfProfiles.copy()

        # creating the Gordon Surface = s_u + s_v - tps by adding the control points
        for cp_u_idx in range(1, self.gordonSurf.NbUPoles+1): #(int cp_u_idx = 1; cp_u_idx <= self.gordonSurf->NbUPoles(); ++cp_u_idx) {
            for cp_v_idx in range(1, self.gordonSurf.NbVPoles+1): #(int cp_v_idx = 1; cp_v_idx <= self.gordonSurf->NbVPoles(); ++cp_v_idx) {
                cp_surf_u = self.skinningSurfProfiles.getPole(cp_u_idx, cp_v_idx)
                cp_surf_v = self.skinningSurfGuides.getPole(cp_u_idx, cp_v_idx)
                cp_tensor = self.tensorProdSurf.getPole(cp_u_idx, cp_v_idx)
                self.gordonSurf.setPole(cp_u_idx, cp_v_idx, cp_surf_u + cp_surf_v - cp_tensor)
    def check_curve_network_compatibility(self, profiles, guides, intersection_params_spline_u, intersection_params_spline_v, tol):
        # find out the 'average' scale of the B-splines in order to being able to handle a more approximate dataset and find its intersections
        bsa = BSplineAlgorithms(self.par_tol)
        splines_scale = 0.5 * (bsa.scale(profiles) + bsa.scale(guides))

        if abs(intersection_params_spline_u[0]) > (splines_scale * tol) or abs(intersection_params_spline_u[-1] - 1.) > (splines_scale * tol):
            self.error("WARNING: B-splines in u-direction must not stick out, spline network must be 'closed'!")
        if abs(intersection_params_spline_v[0]) > (splines_scale * tol) or abs(intersection_params_spline_v[-1] - 1.) > (splines_scale * tol):
            self.error("WARNING: B-splines in v-direction mustn't stick out, spline network must be 'closed'!")

        # check compatibility of network
        #ucurves = list()
        #vcurves = list()
        self.error("\n\ncheck_curve_network_compatibility (L1270)")
        for u_param_idx in range(len(intersection_params_spline_u)): #(size_t u_param_idx = 0; u_param_idx < intersection_params_spline_u.size(); ++u_param_idx) {
            spline_u_param = intersection_params_spline_u[u_param_idx]
            spline_v = guides[u_param_idx]
            #vcurves.append(spline_v.toShape())
            for v_param_idx in range(len(intersection_params_spline_v)): #(size_t v_param_idx = 0; v_param_idx < intersection_params_spline_v.size(); ++v_param_idx) {
                spline_u = profiles[v_param_idx]
                #ucurves.append(spline_u.toShape())
                spline_v_param = intersection_params_spline_v[v_param_idx]
                self.error("spline_u_param, spline_v_param = %0.5f,%0.5f"%(spline_u_param, spline_v_param))
                p_prof = spline_u.value(spline_u_param)
                p_guid = spline_v.value(spline_v_param)
                self.error("p_prof, p_guid = %s,%s"%(p_prof, p_guid))
                distance = p_prof.distanceToPoint(p_guid)
                self.error("distance = %f"%(distance))
                if (distance > splines_scale * tol):
                    self.error("B-spline network is incompatible (e.g. wrong parametrization) or intersection parameters are in a wrong order!")
                self.error("")
        #Part.show(Part.Compound(ucurves))
        #Part.show(Part.Compound(vcurves))

class InterpolateCurveNetwork(object):
    """Bspline surface interpolating a network of curves"""
    def __init__(self, profiles, guides, tol=1e-5, tol2=1e-10):
        self.tolerance = 1e-5
        self.par_tolerance = 1e-10
        self.has_performed = False
        if (len(profiles) < 2) or (len(guides) < 2):
            self.error("Not enough guides or profiles")
        else:
            self.profiles = profiles
            self.guides = guides
        if tol > 0.0:
            self.tolerance = tol
        if tol2 > 0.0:
            self.par_tolerance = tol2
    def error(self,mes):
        print(mes)
    def perform(self):
        if self.has_performed:
            return()
        debug("-> ")
        self.make_curves_compatible()
        debug("-> make_curves_compatible -> OK")
        builder = GordonSurfaceBuilder(self.profiles, self.guides, self.intersectionParamsU, self.intersectionParamsV, self.tolerance, self.par_tolerance)
        debug("-> GordonSurfaceBuilder -> OK")
        self.gordon_surf = builder.surface_gordon()
        debug("-> builder.surface_gordon -> OK")
        self.skinning_surf_profiles = builder.surface_profiles()
        debug("-> builder.surface_profiles -> OK")
        self.skinning_surf_guides = builder.surface_guides()
        debug("-> builder.surface_guides -> OK")
        self.tensor_prod_surf = builder.surface_intersections()
        self.has_performed = True
    def surface_profiles(self):
        self.perform()
        return(self.skinning_surf_profiles)
    def surface_guides(self):
        self.perform()
        return(self.skinning_surf_guides)
    def surface_intersections(self):
        self.perform()
        return(self.tensor_prod_surf)
    def parameters_profiles(self):
        self.perform()
        return(self.intersection_params_v)
    def parameters_guides(self):
        self.perform()
        return(self.intersection_params_u)
    def surface(self):
        self.perform()
        return(self.gordon_surf)
    def compute_intersections(self, intersection_params_u, intersection_params_v):
        debug("\ncompute_intersections")
        for spline_u_idx in range(len(self.profiles)):
            for spline_v_idx in range(len(self.guides)):
                
                currentIntersections = BSplineAlgorithms(self.par_tolerance).intersections(self.profiles[spline_u_idx], self.guides[spline_v_idx], self.par_tolerance)
                if len(currentIntersections) < 1:
                    self.error("U-directional B-spline and v-directional B-spline don't intersect each other!")
                    self.error("profile %d / guide %d"%(spline_u_idx, spline_v_idx))
                elif len(currentIntersections) == 1:
                    intersection_params_u[spline_u_idx][spline_v_idx] = currentIntersections[0][0]
                    intersection_params_v[spline_u_idx][spline_v_idx] = currentIntersections[0][1]
                    # for closed curves
                elif len(currentIntersections) == 2:
                    debug("*** 2 intersections")
                    debug(currentIntersections)
                    # only the u-directional B-spline curves are closed
                    if (self.profiles[0].isClosed()):
                        debug("U-closed")
                        if (spline_v_idx == 0):
                            intersection_params_u[spline_u_idx][spline_v_idx] = min(currentIntersections[0][0], currentIntersections[1][0])
                        elif (spline_v_idx == len(self.guides) - 1):
                            intersection_params_u[spline_u_idx][spline_v_idx] = max(currentIntersections[0][0], currentIntersections[1][0])
                        # intersection_params_vector[0].second == intersection_params_vector[1].second
                        intersection_params_v[spline_u_idx][spline_v_idx] = currentIntersections[0][1]
   
                    # only the v-directional B-spline curves are closed
                    if (self.guides[0].isClosed()):
                        debug("V-closed")
                        if (spline_u_idx == 0):
                            intersection_params_v[spline_u_idx][spline_v_idx] = min(currentIntersections[0][1], currentIntersections[1][1])
                        elif (spline_u_idx == len(self.profiles) - 1):
                            intersection_params_v[spline_u_idx][spline_v_idx] = max(currentIntersections[0][1], currentIntersections[1][1])
                        # intersection_params_vector[0].first == intersection_params_vector[1].first
                        intersection_params_u[spline_u_idx][spline_v_idx] = currentIntersections[0][0]
                    # TODO: both u-directional splines and v-directional splines are closed
                    # elif len(currentIntersections) == 4:
                    debug("%dx%d = (%.4f, %.4f)"%(spline_u_idx, spline_v_idx, intersection_params_u[spline_u_idx][spline_v_idx], intersection_params_v[spline_u_idx][spline_v_idx]))
                else:
                    self.error("U-directional B-spline and v-directional B-spline have more than two intersections with each other!")
    def sort_curves(self, intersection_params_u, intersection_params_v):
        import curve_network_sorter
        sorterObj = curve_network_sorter.CurveNetworkSorter(self.profiles, self.guides, intersection_params_u, intersection_params_v)
        sorterObj.Perform()

        # get the sorted matrices and vectors
        intersection_params_u = sorterObj.parmsIntersProfiles
        intersection_params_v = sorterObj.parmsIntersGuides

        # TODO check the code below
        # copy sorted curves back into our curve arrays
        #struct Caster {
            #Handle(Geom_BSplineCurve) operator()(const Handle(Geom_Curve)& curve) {
                #return Handle(Geom_BSplineCurve)::DownCast(curve);
            #}
        #} caster;

        #std::transform(sorterObj.Profiles().begin(), sorterObj.Profiles().end(), m_profiles.begin(), caster);
        #std::transform(sorterObj.Guides().begin(), sorterObj.Guides().end(), m_guides.begin(), caster);
        self.profiles = sorterObj.profiles
        self.guides = sorterObj.guides
    def make_curves_compatible(self):
        # reparametrize into [0,1]
        bsa = BSplineAlgorithms()
        for c in self.profiles:
            bsa.reparametrizeBSpline(c, 0., 1., self.par_tolerance)
        for c in self.guides:
            bsa.reparametrizeBSpline(c, 0., 1., self.par_tolerance)
        # now the parameter range of all  profiles and guides is [0, 1]

        nGuides = len(self.guides)
        nProfiles = len(self.profiles)
        # now find all intersections of all B-splines with each other
        intersection_params_u = [[0]*nGuides for k in range(nProfiles)] #(0, nProfiles - 1, 0, nGuides - 1);
        intersection_params_v = [[0]*nGuides for k in range(nProfiles)] #(0, nProfiles - 1, 0, nGuides - 1);
        self.compute_intersections(intersection_params_u, intersection_params_v)
        debug("------make_curves_compatible------")
        debug("intersection_params_u\n%s"%intersection_params_u)
        debug("intersection_params_v\n%s"%intersection_params_v)
        # sort intersection_params_u and intersection_params_v and u-directional and v-directional B-spline curves
        self.sort_curves(intersection_params_u, intersection_params_v)

        # eliminate small inaccuracies of the intersection parameters:
        self.eliminate_inaccuracies_network_intersections(self.profiles, self.guides, intersection_params_u, intersection_params_v)

        newParametersProfiles = list()
        for spline_v_idx in range(1, nGuides+1): #(int spline_v_idx = 1; spline_v_idx <= nGuides; ++spline_v_idx) {
            summ = 0
            for spline_u_idx in range(1, nProfiles+1):
                summ += intersection_params_u[spline_u_idx - 1][spline_v_idx - 1]
            newParametersProfiles.append(summ / nProfiles)

        newParametersGuides = list()
        for spline_u_idx in range(1, nProfiles+1):
            summ = 0
            for spline_v_idx in range(1, nGuides+1):
                summ += intersection_params_v[spline_u_idx - 1][spline_v_idx - 1]
            newParametersGuides.append(summ / nGuides)

        debug("newParametersProfiles\n%s"%newParametersProfiles)
        debug("newParametersGuides\n%s"%newParametersGuides)

        if (newParametersProfiles[0] > self.tolerance or newParametersGuides[0] > self.tolerance):
            self.error("At least one B-splines has no intersection at the beginning.")

        # Get maximum number of control points to figure out detail of spline
        max_cp_u = 0
        max_cp_v = 0
        for c in self.profiles:
            max_cp_u = max(max_cp_u, c.NbPoles)
        for c in self.guides:
            max_cp_v = max(max_cp_v, c.NbPoles)

        # we want to use at least 10 and max 80 control points to be able to reparametrize the geometry properly
        mincp = 10
        maxcp = 80

        # since we interpolate the intersections, we cannot use fewer control points than curves
        # We need to add two since we want c2 continuity, which adds two equations
        min_u = max(nGuides + 2, mincp)
        min_v = max(nProfiles + 2, mincp)

        max_u = max(min_u, maxcp);
        max_v = max(min_v, maxcp);
        
        # Clamp(val, min, max) : return std::max(min, std::min(val, max));
        max_cp_u = max(min_u, min(max_cp_u + 10, max_u))
        max_cp_v = max(min_v, min(max_cp_v + 10, max_v))

        # reparametrize u-directional B-splines
        for spline_u_idx in range(nProfiles): #(int spline_u_idx = 0; spline_u_idx < nProfiles; ++spline_u_idx) {
            oldParametersProfile = list()
            for spline_v_idx in range(nGuides):
                oldParametersProfile.append(intersection_params_u[spline_u_idx][spline_v_idx])
            # eliminate small inaccuracies at the first knot
            if (abs(oldParametersProfile[0]) < self.tolerance):
                oldParametersProfile[0] = 0.
            if (abs(newParametersProfiles[0]) < self.tolerance):
                newParametersProfiles[0] = 0.
            # eliminate small inaccuracies at the last knot
            if (abs(oldParametersProfile[-1] - 1.) < self.tolerance):
                oldParametersProfile[-1] = 1.
            if (abs(newParametersProfiles[-1] - 1.) < self.tolerance):
                newParametersProfiles[-1] = 1.

            profile = self.profiles[spline_u_idx]
            profile = bsa.reparametrizeBSplineContinuouslyApprox(profile, oldParametersProfile, newParametersProfiles, max_cp_u)

        # reparametrize v-directional B-splines
        for spline_v_idx in range(nGuides):
            oldParameterGuide = list()
            for spline_u_idx in range(nProfiles):
                oldParameterGuide.append(intersection_params_v[spline_u_idx][spline_v_idx])
            # eliminate small inaccuracies at the first knot
            if (abs(oldParameterGuide[0]) < self.tolerance):
                oldParameterGuide[0] = 0.
            if (abs(newParametersGuides[0]) < self.tolerance):
                newParametersGuides[0] = 0.
            # eliminate small inaccuracies at the last knot
            if (abs(oldParameterGuide[-1] - 1.) < self.tolerance):
                oldParameterGuide[-1] = 1.
            if (abs(newParametersGuides[-1] - 1.) < self.tolerance):
                newParametersGuides[-1] = 1.

            guide = self.guides[spline_v_idx]
            guide = bsa.reparametrizeBSplineContinuouslyApprox(guide, oldParameterGuide, newParametersGuides, max_cp_v)
            
        self.intersectionParamsU = newParametersProfiles
        self.intersectionParamsV = newParametersGuides
    def eliminate_inaccuracies_network_intersections(self, sortedProfiles, sortedGuides, intersection_params_u, intersection_params_v):
        nProfiles = len(sortedProfiles)
        nGuides = len(sortedGuides)
        #tol = 0.001
        # eliminate small inaccuracies of the intersection parameters:

        # first intersection
        for spline_u_idx in range(nProfiles):
            if (abs(intersection_params_u[spline_u_idx][0] - sortedProfiles[0].getKnot(1)) < self.tolerance):
                if (abs(sortedProfiles[0].getKnot(1)) < self.par_tolerance):
                    intersection_params_u[spline_u_idx][0] = 0
                else:
                    intersection_params_u[spline_u_idx][0] = sortedProfiles[0].getKnot(1)

        for spline_v_idx in range(nGuides):
            if (abs(intersection_params_v[0][spline_v_idx] - sortedGuides[0].getKnot(1)) < self.tolerance):
                if (abs(sortedGuides[0].getKnot(1)) < self.par_tolerance):
                    intersection_params_v[0][spline_v_idx] = 0
                else:
                    intersection_params_v[0][spline_v_idx] = sortedGuides[0].getKnot(1)

        # last intersection
        for spline_u_idx in range(nProfiles):
            if (abs(intersection_params_u[spline_u_idx][nGuides - 1] - sortedProfiles[0].getKnot(sortedProfiles[0].NbKnots)) < self.tolerance):
                intersection_params_u[spline_u_idx][nGuides - 1] = sortedProfiles[0].getKnot(sortedProfiles[0].NbKnots)

        for spline_v_idx in range(nGuides):
            if (abs(intersection_params_v[nProfiles - 1][spline_v_idx] - sortedGuides[0].getKnot(sortedGuides[0].NbKnots)) < self.tolerance):
                intersection_params_v[nProfiles - 1][spline_v_idx] = sortedGuides[0].getKnot(sortedGuides[0].NbKnots)

def main():
    
    import FreeCAD
    import FreeCADGui
    import Part
    
    data = ["test-S2R-2","Compound","Compound001"]
    #data = ["Gordon-sphere","Compound","Compound001"]
    data = ["test-birail-3","Compound","Compound001"]
    #data = ["Gordon-2","profiles","guides"]
    
    doc = FreeCAD.open(u"/home/tomate/.FreeCAD/Mod/CurvesWB/TestFiles/%s.fcstd"%data[0])
    # Create array of curves
    guide_edges = doc.getObject(data[1]).Shape.Edges
    profile_edges = doc.getObject(data[2]).Shape.Edges
    guide_curves = [e.Curve.toBSpline() for e in guide_edges]
    profile_curves = [e.Curve.toBSpline() for e in profile_edges]

    # create the gordon surface
    gordon = InterpolateCurveNetwork(profile_curves, guide_curves, 1e-5)

    # display curves and resulting surface
    Part.show(gordon.surface().toShape())
    FreeCAD.ActiveDocument.recompute()

if __name__ == "__main__":
    main()




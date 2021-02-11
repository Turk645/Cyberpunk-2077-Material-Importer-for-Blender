bl_info = {
    "name": "Cyberpunk 2077 Mlsetup Import",
    "author": "Turk",
    "version": (1, 0, 0),
    "blender": (2, 82, 0),
    "location": "File > Import-Export",
    "description": "A script to import mlsetup json",
    "warning": "",
    "category": "Import-Export",
}
import sys
import bpy
import os
import io
import struct
import math
import mathutils
import json

from bpy.props import (BoolProperty,
                       FloatProperty,
                       StringProperty,
                       EnumProperty,
                       CollectionProperty
                       )
from bpy_extras.io_utils import ImportHelper

class CP77MLSImp(bpy.types.Operator, ImportHelper):
    """Imports the selected MLSetup onto the current active mesh"""
    bl_idname = "custom_import_scene.cp77mlsetup"
    bl_label = "Import MLSetup"
    #bl_options = {'PRESET', 'UNDO'}
    filter_glob: StringProperty(
            default="*.mlsetup.json",
            options={'HIDDEN'},
            )
    filepath: StringProperty(subtype='FILE_PATH',)
    files: CollectionProperty(type=bpy.types.PropertyGroup)
    flipMaskY: BoolProperty(
        name = "Y flip masks",
        description = "Flip the imported masks on the Y axis. Needed depending on the mesh output method",
        default=False,
        )
    TestEnum = EnumProperty(
        name="Test",
        description="ShitPickle",
        items=(1,2,3),
        default=1,
        )
    
    def draw(self, context):
        layout = self.layout
        layout.prop(self, "flipMaskY")
        layout.prop(self, "TestEnum")
    def execute(self, context):
        bpy.ops.object.custom_draw_mlmask_get('INVOKE_DEFAULT',MLSetup = self.filepath,flipMaskY=self.flipMaskY)
        return {'FINISHED'}


class CustomDrawOperatorMLMask(bpy.types.Operator):  #This on holds the actual creation code
    bl_idname = "object.custom_draw_mlmask_get"
    bl_label = "Import MLMask"
    
    filter_glob: StringProperty(
            default="*.mlmask",
            options={'HIDDEN'},
            )
 
    filepath: StringProperty(subtype='FILE_PATH',)
    files: CollectionProperty(type=bpy.types.PropertyGroup)
    MLSetup: StringProperty("")
    flipMaskY: BoolProperty(False)
    def execute(self, context):
        print("MLSetup file is " + os.path.basename(self.MLSetup))
        print("MLMask file is " +os.path.basename(self.filepath))
        BasePath = self.MLSetup[:self.MLSetup.find("\\base\\")+1]
        mltemplates = []
        with open(self.MLSetup) as f:
            mlsetup = json.load(f)
        mlimp = mlsetup.get("Imports")
        xllay = mlsetup["Chunks"][0]["data"]["Layers"]
        LayerCount = len(xllay)
        
        
        #tempremove node groups on run
        # for x in bpy.data.node_groups:
            # bpy.data.node_groups.remove(x)
        
        for x in (mlimp):
            depot = x.get("DepotPathStr")
            if depot and depot[-10:] == "mltemplate":
                #mltemplates.append(BasePath+depot)
                mlname = os.path.basename(depot)
                if not bpy.data.node_groups.get(mlname):
                    createBaseMaterial(mlname,BasePath+depot+".json",BasePath)
                    continue
        LayerIndex = 0
        CurMat = bpy.context.active_object.active_material.node_tree
        for x in (xllay):            
            MatTile = x["MatTile"]
            MbTile = x.get("MbTile")
            MbScale = 1
            if MatTile: 
                MbScale = float(MatTile["val"])
            if MbTile:
                MbScale = float(MbTile["val"])
            Microblend = x["Microblend"]
            MicroblendContrast = x["MicroblendContrast"]
            microblendNormalStrength = x.get("microblendNormalStrength")
            if not microblendNormalStrength:
                microblendNormalStrength = x.get("MicroblendNormalStrength")
            opacity = x.get("opacity")
            if not opacity:
                opacity = x.get("Opacity")
            material = x.get("material")
            if not material:
                material = x.get("Material")
            colorScale = x.get("colorScale")
            if not colorScale:
                colorScale = x.get("ColorScale")
            normalStrength = x.get("normalStrength")
            if not normalStrength:
                normalStrength = x.get("NormalStrength")
            #roughLevelsIn = x["roughLevelsIn"]
            roughLevelsOut = x.get("roughLevelsOut")
            if not roughLevelsOut:
                roughLevelsOut = x.get("RoughLevelsOut")
            #metalLevelsIn = x["metalLevelsIn"]
            metalLevelsOut = x.get("metalLevelsOut")
            if not metalLevelsOut:
                metalLevelsOut = x.get("MetalLevelsOut")
            
            if Microblend != "null" and Microblend["DepotPath"] != "null":
                MBI = imageFromPath(BasePath+Microblend["DepotPath"][:-3]+"png",True)
            
            OverrideTable = createOverrideTable(BasePath+material["DepotPath"]+".json")#get override info for colors and what not

            
            NG = bpy.data.node_groups.new(os.path.basename(self.MLSetup)+"_Layer_"+str(LayerIndex),"ShaderNodeTree")#create layer's node group
            NG.outputs.new('NodeSocketColor','Difuse')
            NG.outputs.new('NodeSocketColor','Normal')
            NG.outputs.new('NodeSocketColor','Roughness')
            NG.outputs.new('NodeSocketColor','Metallic')
            NG.outputs.new('NodeSocketColor','Opacity')
            
            LayerGroupN = CurMat.nodes.new("ShaderNodeGroup")
            LayerGroupN.location = (-2000,500-100*LayerIndex)
            LayerGroupN.hide = True
            LayerGroupN.width = 400
            LayerGroupN.node_tree = NG
            LayerGroupN.name = "Mat_Mod_Layer_"+str(LayerIndex)
            LayerIndex += 1
            
            GroupOutN = NG.nodes.new("NodeGroupOutput")
            GroupOutN.hide=True
            GroupOutN.location = (0,0)
            
            BaseMat = bpy.data.node_groups.get(os.path.basename(material["DepotPath"]))
            if BaseMat:
                BMN = NG.nodes.new("ShaderNodeGroup")
                BMN.location = (-2000,0)
                BMN.hide = True
                BMN.node_tree = BaseMat
            
            OpacN = NG.nodes.new("ShaderNodeValue")
            OpacN.hide=True
            OpacN.location = (-200,-10)
            OpacN.outputs[0].default_value = 1
            if opacity:
                OpacN.outputs[0].default_value = float(opacity["val"])
            
            TileMultN = NG.nodes.new("ShaderNodeValue")
            TileMultN.location = (-2200,0)
            TileMultN.hide = True
            if MatTile != None and MatTile["val"] != "null":
                TileMultN.outputs[0].default_value = float(MatTile["val"])
            else:
                TileMultN.outputs[0].default_value = 1

            if colorScale != "null" and colorScale["Value"] != "null":
                ColorScaleN = NG.nodes.new("ShaderNodeRGB")
                ColorScaleN.hide=True
                ColorScaleN.location=(-2000,-45)
                ColorScaleN.outputs[0].default_value = OverrideTable["ColorScale"][colorScale["Value"]]
                #add color info shit here
                
                ColorScaleMixN = NG.nodes.new("ShaderNodeMixRGB")
                ColorScaleMixN.hide=True
                ColorScaleMixN.location=(-1800,0)
                ColorScaleMixN.inputs[0].default_value=1
                ColorScaleMixN.blend_type='MULTIPLY'

            GeoN = NG.nodes.new("ShaderNodeNewGeometry")
            GeoN.hide=True
            GeoN.location=(-1960.0, -200.0)
            
            NormSubN = NG.nodes.new("ShaderNodeVectorMath")
            NormSubN.hide=True
            NormSubN.location = (-1780.0, -200.0)
            NormSubN.operation = 'SUBTRACT'
            
            
            MBN = NG.nodes.new("ShaderNodeTexImage")
            MBN.hide = True
            MBN.image = MBI
            MBN.location = (-1800,-100)
            MBN.label = "Microblend"
            MBN.texture_mapping.scale = (MbScale,MbScale,MbScale)
            
            MBNormStrengthN = NG.nodes.new("ShaderNodeNormalMap")
            MBNormStrengthN.hide = True
            MBNormStrengthN.location = (-1500,-100)
            if microblendNormalStrength:
                MBNormStrengthN.inputs[0].default_value = float(microblendNormalStrength["val"])
                
            NormStrengthN = NG.nodes.new("ShaderNodeNormalMap")
            NormStrengthN.hide = True
            NormStrengthN.location = (-1800,-150)
            NormStrengthN.inputs[0].default_value = OverrideTable["NormalStrength"][normalStrength["Value"]]
            
            RoughRampN = NG.nodes.new("ShaderNodeMapRange")
            RoughRampN.hide=True
            RoughRampN.location = (-1800,-250)
            RoughRampN.inputs['To Min'].default_value = (OverrideTable["RoughLevelsOut"][roughLevelsOut["Value"]][1][0])
            RoughRampN.inputs['To Max'].default_value = (OverrideTable["RoughLevelsOut"][roughLevelsOut["Value"]][0][0])
            RoughRampN.label = "Roughness Ramp"
                
            RoughRamp2N = NG.nodes.new("ShaderNodeMapRange")
            RoughRamp2N.hide=True
            RoughRamp2N.location = (-1500,-250)
            RoughRamp2N.inputs['From Max'].default_value = 0.5
            RoughRamp2N.label = "Roughness Ramp 2"
                
            MetalRampN = NG.nodes.new("ShaderNodeValToRGB")
            MetalRampN.hide=True
            MetalRampN.location = (-1800,-300)
            MetalRampN.color_ramp.elements[1].color = (OverrideTable["MetalLevelsOut"][metalLevelsOut["Value"]][0])
            MetalRampN.color_ramp.elements[0].color = (OverrideTable["MetalLevelsOut"][metalLevelsOut["Value"]][1])
            MetalRampN.label = "Metal Ramp"
            
            NormalCombineN = NG.nodes.new("ShaderNodeVectorMath")
            NormalCombineN.hide = True
            NormalCombineN.location = (-1500,-150)
            
            NormalizeN = NG.nodes.new("ShaderNodeVectorMath")
            NormalizeN.hide = True
            NormalizeN.location = (-1300,-150)
            NormalizeN.operation = 'NORMALIZE'
            
                
            NG.links.new(TileMultN.outputs[0],BMN.inputs[0])
            NG.links.new(BMN.outputs[0],ColorScaleMixN.inputs[1])
            NG.links.new(ColorScaleN.outputs[0],ColorScaleMixN.inputs[2])
            NG.links.new(BMN.outputs[1],NormStrengthN.inputs[1])
            NG.links.new(MBN.outputs[0],MBNormStrengthN.inputs[1])
            NG.links.new(BMN.outputs[2],RoughRampN.inputs[0])
            NG.links.new(BMN.outputs[3],MetalRampN.inputs[0])
            NG.links.new(RoughRampN.outputs[0],RoughRamp2N.inputs[0])
            NG.links.new(RoughRamp2N.outputs[0],GroupOutN.inputs[2])
            NG.links.new(MetalRampN.outputs[0],GroupOutN.inputs[3])
            NG.links.new(NormStrengthN.outputs[0],NormalCombineN.inputs[0])
            NG.links.new(MBNormStrengthN.outputs[0],NormSubN.inputs[0])
            NG.links.new(GeoN.outputs['Normal'],NormSubN.inputs[1])
            NG.links.new(NormSubN.outputs[0],NormalCombineN.inputs[1])
            NG.links.new(NormalCombineN.outputs[0],NormalizeN.inputs[0])
            NG.links.new(NormalizeN.outputs[0],GroupOutN.inputs[1])
            NG.links.new(ColorScaleMixN.outputs[0],GroupOutN.inputs[0])
            NG.links.new(OpacN.outputs[0],GroupOutN.inputs[4])
            
        createLayerMaterial(os.path.basename(self.MLSetup)+"_Layer_",LayerCount,CurMat,self)
        return {'FINISHED'}
    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}
def imageFromPath(Img,isNormal = False):
    Im = bpy.data.images.get(os.path.basename(Img))
    if not Im:
        Im = bpy.data.images.new(os.path.basename(Img),1,1)
        Im.source = "FILE"
        Im.filepath = Img[:-3]+"png"
        if isNormal:
            Im.colorspace_settings.name = 'Non-Color'
    return Im

def createBaseMaterial(matname,matpath,BasePath):
    #print("Attempting to create "+matname)
    with open(matpath) as f:
        matjson = json.load(f)
    matdata = matjson["Chunks"][0]["data"]
    CT = imageFromPath(BasePath+matdata["ColorTexture"]["DepotPath"])
    NT = imageFromPath(BasePath+matdata["NormalTexture"]["DepotPath"],isNormal = True)
    RT = imageFromPath(BasePath+matdata["RoughnessTexture"]["DepotPath"])
    MT = imageFromPath(BasePath+matdata["MetalnessTexture"]["DepotPath"])
    TileMult = matdata["TilingMultiplier"]
    if not TileMult:
        TileMult = 1
    else:
        TileMult = float(TileMult["val"])
    # print("\t"+matdata["ColorTexture"]["DepotPath"])
    # print("\t"+matdata["NormalTexture"]["DepotPath"])
    # print("\t"+matdata["RoughnessTexture"]["DepotPath"])
    # print("\t"+matdata["MetalnessTexture"]["DepotPath"])
    # print("\n")
    NG = bpy.data.node_groups.new(matname,"ShaderNodeTree")
    TMI = NG.inputs.new('NodeSocketVector','Tile Multiplier')
    TMI.default_value = (1,1,1)
    NG.outputs.new('NodeSocketColor','Difuse')
    NG.outputs.new('NodeSocketColor','Normal')
    NG.outputs.new('NodeSocketColor','Roughness')
    NG.outputs.new('NodeSocketColor','Metallic')
    
    CTN = NG.nodes.new("ShaderNodeTexImage")
    CTN.hide = True
    CTN.image = CT
    
    NTN = NG.nodes.new("ShaderNodeTexImage")
    NTN.hide = True
    NTN.image = NT
    NTN.location[1] = -45*1
    
    RTN = NG.nodes.new("ShaderNodeTexImage")
    RTN.hide = True
    RTN.image = RT
    RTN.location[1] = -45*2
    
    MTN = NG.nodes.new("ShaderNodeTexImage")
    MTN.hide = True
    MTN.image = MT
    MTN.location[1] = -45*3
    
    MapN = NG.nodes.new("ShaderNodeMapping")
    MapN.hide = True
    MapN.location = (-310,-64)
    
    TexCordN = NG.nodes.new("ShaderNodeTexCoord")
    TexCordN.hide = True
    TexCordN.location = (-500,-64)
    
    TileMultN = NG.nodes.new("ShaderNodeValue")
    TileMultN.location = (-700,-45*2)
    TileMultN.hide = True
    TileMultN.outputs[0].default_value = TileMult
    
    GroupInN = NG.nodes.new("NodeGroupInput")
    GroupInN.location = (-700,-45*4)
    GroupInN.hide = True
    
    GroupOutN = NG.nodes.new("NodeGroupOutput")
    GroupOutN.hide=True
    GroupOutN.location = (400,0)
    
    VecMathN = NG.nodes.new("ShaderNodeVectorMath")
    VecMathN.hide=True
    VecMathN.location = (-500,-45*3)
    VecMathN.operation = 'MULTIPLY'
    
    NormSepN = NG.nodes.new("ShaderNodeSeparateRGB")
    NormSepN.hide=True
    
    NormCombN = NG.nodes.new("ShaderNodeCombineRGB")
    NormCombN.hide=True
    NormCombN.location = (100,0)
    NormCombN.inputs[2].default_value = 1
    
    NG.links.new(TexCordN.outputs['UV'],MapN.inputs['Vector'])
    NG.links.new(VecMathN.outputs[0],MapN.inputs['Scale'])
    NG.links.new(MapN.outputs['Vector'],CTN.inputs['Vector'])
    NG.links.new(MapN.outputs['Vector'],NTN.inputs['Vector'])
    NG.links.new(MapN.outputs['Vector'],RTN.inputs['Vector'])
    NG.links.new(MapN.outputs['Vector'],MTN.inputs['Vector'])
    NG.links.new(TileMultN.outputs[0],VecMathN.inputs[0])
    NG.links.new(GroupInN.outputs[0],VecMathN.inputs[1])
    NG.links.new(CTN.outputs[0],GroupOutN.inputs[0])
    NG.links.new(NTN.outputs[0],NormSepN.inputs[0])
    NG.links.new(RTN.outputs[0],GroupOutN.inputs[2])
    NG.links.new(MTN.outputs[0],GroupOutN.inputs[3])
    NG.links.new(NormSepN.outputs[0],NormCombN.inputs[0])
    NG.links.new(NormSepN.outputs[1],NormCombN.inputs[1])
    NG.links.new(NormCombN.outputs[0],GroupOutN.inputs[1])
    
    return

def createOverrideTable(matpath):
    #print(matpath)
    with open(matpath) as f:
        matjson = json.load(f)
    OverList = matjson["Chunks"][0]["data"]["Overrides"]
    Output = {}
    Output["ColorScale"] = {}
    Output["NormalStrength"] = {}
    Output["RoughLevelsOut"] = {}
    Output["MetalLevelsOut"] = {}
    for x in OverList["ColorScale"]:
        tmpName = x["N"]["Value"]
        tmpR = float(x["V"][0]["val"])
        tmpG = float(x["V"][1]["val"])
        tmpB = float(x["V"][2]["val"])
        Output["ColorScale"][tmpName] = (tmpR,tmpG,tmpB,1)
    for x in OverList["NormalStrength"]:
        tmpName = x["N"]["Value"]
        tmpStrength = x["V"]
        if tmpStrength:
            tmpStrength = float(tmpStrength["val"])
        else:
            tmpStrength = 0
        Output["NormalStrength"][tmpName] = tmpStrength
    for x in OverList["RoughLevelsOut"]:
        tmpName = x["N"]["Value"]
        tmpStrength0 = float(x["V"][0]["val"])
        tmpStrength1 = float(x["V"][1]["val"])
        Output["RoughLevelsOut"][tmpName] = [(tmpStrength0,tmpStrength0,tmpStrength0,1),(tmpStrength1,tmpStrength1,tmpStrength1,1)]
    for x in OverList["MetalLevelsOut"]:
        tmpName = x["N"]["Value"]
        if x["V"]:
            tmpStrength0 = float(x["V"][0]["val"])
            tmpStrength1 = float(x["V"][1]["val"])
        else:
            tmpStrength0 = 0
            tmpStrength1 = 1
        Output["MetalLevelsOut"][tmpName] = [(tmpStrength0,tmpStrength0,tmpStrength0,1),(tmpStrength1,tmpStrength1,tmpStrength1,1)]
    return Output

def createLayerMaterial(LayerName,LayerCount,CurMat,self):
    for x in range(LayerCount-1):
        MaskTexture = imageFromPath(os.path.splitext(self.filepath)[0]+"_"+str(x+1)+".png")
        NG = bpy.data.node_groups.new("Layer_Blend_"+str(x),"ShaderNodeTree")#create layer's node group
        NG.inputs.new('NodeSocketColor','Difuse1')
        NG.inputs.new('NodeSocketColor','Normal1')
        NG.inputs.new('NodeSocketColor','Roughness1')
        NG.inputs.new('NodeSocketColor','Metallic1')
        NG.inputs.new('NodeSocketColor','Difuse2')
        NG.inputs.new('NodeSocketColor','Normal2')
        NG.inputs.new('NodeSocketColor','Roughness2')
        NG.inputs.new('NodeSocketColor','Metallic2')
        NG.inputs.new('NodeSocketColor','Mask')
        NG.outputs.new('NodeSocketColor','Difuse')
        NG.outputs.new('NodeSocketColor','Normal')
        NG.outputs.new('NodeSocketColor','Roughness')
        NG.outputs.new('NodeSocketColor','Metallic')
        
        GroupInN = NG.nodes.new("NodeGroupInput")
        GroupInN.location = (-700,0)
        GroupInN.hide = True
        
        GroupOutN = NG.nodes.new("NodeGroupOutput")
        GroupOutN.hide=True
        GroupOutN.location = (200,0)
        
        ColorMixN = NG.nodes.new("ShaderNodeMixRGB")
        ColorMixN.hide=True
        ColorMixN.location = (-300,100)
        ColorMixN.label = "Color Mix"
        
        NormalMixN = NG.nodes.new("ShaderNodeMixRGB")
        NormalMixN.hide=True
        NormalMixN.location = (-300,50)
        NormalMixN.label = "Normal Mix"
        
        RoughMixN = NG.nodes.new("ShaderNodeMixRGB")
        RoughMixN.hide=True
        RoughMixN.location = (-300,0)
        RoughMixN.label = "Rough Mix"
        
        MetalMixN = NG.nodes.new("ShaderNodeMixRGB")
        MetalMixN.hide=True
        MetalMixN.location = (-300,-50)
        MetalMixN.label = "Metal Mix"

        LayerGroupN = CurMat.nodes.new("ShaderNodeGroup")
        LayerGroupN.location = (-1400,450-100*x)
        LayerGroupN.hide = True
        LayerGroupN.node_tree = NG
        LayerGroupN.name = "Layer_"+str(x)
        
        MaskN = CurMat.nodes.new("ShaderNodeTexImage")
        MaskN.hide = True
        MaskN.image = MaskTexture
        MaskN.location = (-2100,450-100*x)
        if self.flipMaskY:
            MaskN.texture_mapping.scale[1] = -1 #flip mask if needed
        MaskN.label="Layer_"+str(x+1)
        
        MaskOpacN = CurMat.nodes.new("ShaderNodeMixRGB")
        MaskOpacN.hide = True
        MaskOpacN.location = (-1800,450-100*x)
        MaskOpacN.inputs[0].default_value = 1
        MaskOpacN.blend_type = "MULTIPLY"
        MaskOpacN.label = "Opacity"
        
        
        if x == 0:
            CurMat.links.new(CurMat.nodes["Mat_Mod_Layer_"+"0"].outputs[0],LayerGroupN.inputs[0])
            CurMat.links.new(CurMat.nodes["Mat_Mod_Layer_"+"0"].outputs[1],LayerGroupN.inputs[1])
            CurMat.links.new(CurMat.nodes["Mat_Mod_Layer_"+"0"].outputs[2],LayerGroupN.inputs[2])
            CurMat.links.new(CurMat.nodes["Mat_Mod_Layer_"+"0"].outputs[3],LayerGroupN.inputs[3])
            CurMat.links.new(CurMat.nodes["Mat_Mod_Layer_"+"1"].outputs[0],LayerGroupN.inputs[4])
            CurMat.links.new(CurMat.nodes["Mat_Mod_Layer_"+"1"].outputs[1],LayerGroupN.inputs[5])
            CurMat.links.new(CurMat.nodes["Mat_Mod_Layer_"+"1"].outputs[2],LayerGroupN.inputs[6])
            CurMat.links.new(CurMat.nodes["Mat_Mod_Layer_"+"1"].outputs[3],LayerGroupN.inputs[7])
        else:
            CurMat.links.new(CurMat.nodes["Layer_"+str(x-1)].outputs[0],LayerGroupN.inputs[0])
            CurMat.links.new(CurMat.nodes["Layer_"+str(x-1)].outputs[1],LayerGroupN.inputs[1])
            CurMat.links.new(CurMat.nodes["Layer_"+str(x-1)].outputs[2],LayerGroupN.inputs[2])
            CurMat.links.new(CurMat.nodes["Layer_"+str(x-1)].outputs[3],LayerGroupN.inputs[3])
            CurMat.links.new(CurMat.nodes["Mat_Mod_Layer_"+str(x+1)].outputs[0],LayerGroupN.inputs[4])
            CurMat.links.new(CurMat.nodes["Mat_Mod_Layer_"+str(x+1)].outputs[1],LayerGroupN.inputs[5])
            CurMat.links.new(CurMat.nodes["Mat_Mod_Layer_"+str(x+1)].outputs[2],LayerGroupN.inputs[6])
            CurMat.links.new(CurMat.nodes["Mat_Mod_Layer_"+str(x+1)].outputs[3],LayerGroupN.inputs[7])
        CurMat.links.new(MaskN.outputs[0],MaskOpacN.inputs[1])
        CurMat.links.new(CurMat.nodes["Mat_Mod_Layer_"+str(x+1)].outputs[4],MaskOpacN.inputs[2])
        CurMat.links.new(MaskOpacN.outputs[0],CurMat.nodes["Layer_"+str(x)].inputs[8])
            
        NG.links.new(GroupInN.outputs[0],ColorMixN.inputs[1])
        NG.links.new(GroupInN.outputs[1],NormalMixN.inputs[1])
        NG.links.new(GroupInN.outputs[2],RoughMixN.inputs[1])
        NG.links.new(GroupInN.outputs[3],MetalMixN.inputs[1])
        NG.links.new(GroupInN.outputs[4],ColorMixN.inputs[2])
        NG.links.new(GroupInN.outputs[5],NormalMixN.inputs[2])
        NG.links.new(GroupInN.outputs[6],RoughMixN.inputs[2])
        NG.links.new(GroupInN.outputs[7],MetalMixN.inputs[2])
        NG.links.new(GroupInN.outputs[8],ColorMixN.inputs[0])
        NG.links.new(GroupInN.outputs[8],NormalMixN.inputs[0])
        NG.links.new(GroupInN.outputs[8],RoughMixN.inputs[0])
        NG.links.new(GroupInN.outputs[8],MetalMixN.inputs[0])
        
        NG.links.new(ColorMixN.outputs[0],GroupOutN.inputs[0])
        NG.links.new(NormalMixN.outputs[0],GroupOutN.inputs[1])
        NG.links.new(RoughMixN.outputs[0],GroupOutN.inputs[2])
        NG.links.new(MetalMixN.outputs[0],GroupOutN.inputs[3])
        
    CurMat.links.new(CurMat.nodes["Layer_"+str(LayerCount-2)].outputs[0],CurMat.nodes['Principled BSDF'].inputs['Base Color'])
    CurMat.links.new(CurMat.nodes["Layer_"+str(LayerCount-2)].outputs[1],CurMat.nodes['Principled BSDF'].inputs['Normal'])
    CurMat.links.new(CurMat.nodes["Layer_"+str(LayerCount-2)].outputs[2],CurMat.nodes['Principled BSDF'].inputs['Roughness'])
    CurMat.links.new(CurMat.nodes["Layer_"+str(LayerCount-2)].outputs[3],CurMat.nodes['Principled BSDF'].inputs['Metallic'])
    return


def menu_func_import(self, context):
    self.layout.operator(CP77MLSImp.bl_idname, text="Cyberpunk MLSetup (.mlsetup.json)")
        
def register():
    bpy.utils.register_class(CP77MLSImp)
    bpy.utils.register_class(CustomDrawOperatorMLMask)
    bpy.types.TOPBAR_MT_file_import.append(menu_func_import)
    
def unregister():
    bpy.utils.unregister_class(CP77MLSImp)
    bpy.utils.unregister_class(CustomDrawOperatorMLMask)
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)
        
if __name__ == "__main__":
    register()
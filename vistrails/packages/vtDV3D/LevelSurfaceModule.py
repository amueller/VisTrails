'''
Created on Dec 2, 2010

@author: tpmaxwel
'''
import vtk
from PyQt4.QtCore import *
from PyQt4.QtGui import *
import core.modules.module_registry
from core.modules.vistrails_module import Module, ModuleError
from packages.vtk.base_module import vtkBaseModule
from core.modules.module_registry import get_module_registry
from core.interpreter.default import get_default_interpreter as getDefaultInterpreter
from core.modules.basic_modules import Integer, Float, String, File, Variant, Color
from packages.vtDV3D.ColorMapManager import ColorMapManager 
from packages.vtDV3D.InteractiveConfiguration import QtWindowLeveler 
from packages.vtDV3D.vtUtilities import *
from packages.vtDV3D.PersistentModule import *
        
class PM_LevelSurface(PersistentVisualizationModule):
    """
        This module generates level surfaces from 3D volumetric (<i>vtkImagedata</i>) data.   The number of levels generated is
    controlled by the <b>nLevels</b> gui function, and the level values are controlled by the <b>levelRangeScale</b> leveling function.  The
    colormap and colorscaling can also be configured by gui and leveling commands respectively.  The <b>opacity</b> of the contours
    is configured using the opacity leveling function. 
    <h3>  Command Keys </h3>   
        <table border="2" bordercolor="#336699" cellpadding="2" cellspacing="2" width="100%">  
        <tr> <th> Command Key </th> <th> Function </th> </tr> 
        <tr> <td> l </td> <td> Toggle show colorbar. </td>
        </table>
    """
           
    def __init__(self, mid, **args):
        PersistentVisualizationModule.__init__(self,  mid, **args)
        self.primaryInputPorts = [ 'volume', 'texture' ]
        self.opacityRange =  [ 0.2, 0.99 ]
        self.numberOfLevels = 1
        self.generateTexture = False
        self.removeConfigurableFunction( 'colormap' )
#        self.addConfigurableLevelingFunction( 'colorScale', 'C', label='Colormap Scale', setLevel=self.setColorScale, getLevel=self.getColorScale, layerDependent=True, adjustRange=True, units='data'  )
        self.addConfigurableLevelingFunction( 'levelRangeScale', 'L', label='Isosurface Level Range', setLevel=self.setLevelRange, getLevel=self.getDataRangeBounds, layerDependent=True, units='data', adjustRange=True )
        self.addConfigurableLevelingFunction( 'isoOpacity', 'p', label='Isosurface Opacity', activeBound='min', setLevel=self.setOpacityRange, getLevel=self.getOpacityRange, layerDependent=True )
        self.addConfigurableGuiFunction( 'nLevels', NLevelConfigurationWidget, 'n', label='# Isosurface Levels', setValue=self.setNumberOfLevels, getValue=self.getNumberOfLevels, layerDependent=True )
        self.addConfigurableLevelingFunction( 'zScale', 'z', label='Vertical Scale', setLevel=self.setInputZScale, activeBound='max', getLevel=self.getScaleBounds, windowing=False, sensitivity=(10.0,10.0), initRange=[ 2.0, 2.0, 1 ] )
        self.addConfigurableLevelingFunction( 'colorScale', 'C', label='Texture Colormap Scale', units='data', setLevel=lambda data:self.setColorScale(data,1), getLevel=lambda:self.getDataRangeBounds(1), layerDependent=True, adjustRange=True, isValid=self.hasTexture )
        self.addConfigurableGuiFunction( 'colormap', ColormapConfigurationDialog, 'c', label='Choose Texture Colormap', setValue=lambda data:self.setColormap(data,1) , getValue=lambda: self.getColormap(1), layerDependent=True, isValid=self.hasTexture )

    def hasTexture(self):
        return self.generateTexture

    def setInputZScale( self, zscale_data, **args  ):       
        texture_ispec = self.getInputSpec(  1 )                
        if texture_ispec and texture_ispec.input:
            textureInput = texture_ispec.input 
            ix, iy, iz = textureInput.GetSpacing()
            sz = zscale_data[1]
            textureInput.SetSpacing( ix, iy, sz )  
            textureInput.Modified() 
        return PersistentVisualizationModule.setInputZScale(self,  zscale_data, **args )
        
    def setOpacityRange( self, opacity_range, **args  ):
        print "Update Opacity, range = %s" %  str( opacity_range )
        self.opacityRange = opacity_range
        cmap_index = 1 if self.generateTexture else 0
        colormapManager = self.getColormapManager( index=cmap_index )
        colormapManager.setAlphaRange ( [ opacity_range[0], opacity_range[0] ]  ) 
#        self.levelSetProperty.SetOpacity( opacity_range[1] )
        
    def setColorScale( self, range, cmap_index=0, **args  ):
        ispec = self.getInputSpec( cmap_index )
        if ispec and ispec.input:
            imageRange = self.getImageValues( range[0:2], cmap_index ) 
            colormapManager = self.getColormapManager( index=cmap_index )
            colormapManager.setScale( imageRange, range )
            self.levelSetMapper.Modified()

    def getColorScale( self, cmap_index=0 ):
        sr = self.getDataRangeBounds( cmap_index )
        return [ sr[0], sr[1], 0 ]

    def getOpacityRange( self ):
        return [ self.opacityRange[0], self.opacityRange[1], 0 ]
         
#    def getLevelRange(self): 
#        level_data_values = self.getDataValues( self.range )
#        print "getLevelRange, data range = %s, image range = %s" % ( str( self.range ),  str( level_data_values ) )
#        level_data_values.append( 0 )
#        return level_data_values
##        return [ self.range[0], self.range[1], 0 ]

    def setNumberOfLevels( self, nLevelsData, **args   ):
        self.numberOfLevels = int( getItem( nLevelsData ) )
        if self.numberOfLevels < 1: self.numberOfLevels = 1
        self.updateLevels()

    def getNumberOfLevels( self ):
        return [ self.numberOfLevels, ]
    
    def setLevelRange( self, range, **args ):
        print "  ---> setLevelRange, data range = %s" % str( range ) 
        self.range = self.getImageValues( range )
        self.updateLevels()
    
    def updateLevels(self):
        self.levelSetFilter.SetNumberOfContours( self.numberOfLevels ) 
        nL1 = self.numberOfLevels + 1
        dL = ( self.range[1] - self.range[0] ) / nL1
        for i in range( 1, nL1 ): self.levelSetFilter.SetValue ( i, self.range[0] + dL * i )    
#        self.updateColorMapping()
        print "Update %d Level(s), range = [ %f, %f ], levels = %s" %  ( self.numberOfLevels, self.range[0], self.range[1], str(self.getLevelValues()) )  
        
#    def updateColorMapping(self):
#        if self.colorByMappedScalars: 
#            pass
#        else:
#            color = self.lut.
#            self.levelSetProperty.SetColor( color )        
        
    def getLevelValues(self):
        return [ self.levelSetFilter.GetValue( iV ) for iV in range( self.levelSetFilter.GetNumberOfContours() ) ]
 
        
    def finalizeConfiguration( self ):
        PersistentVisualizationModule.finalizeConfiguration( self )
        self.levelSetFilter.ComputeNormalsOn()
        self.render()

    def setInteractionState( self, caller, event ):
        PersistentVisualizationModule.setInteractionState( self, caller, event )
        if self.InteractionState <> None: 
            self.levelSetFilter.ComputeNormalsOff()
            self.levelSetFilter.ComputeGradientsOff()

    def updateModule(self, **args ):
        self.inputModule().inputToAlgorithm( self.levelSetFilter ) 
#        self.levelSetFilter.Modified()
        self.set3DOutput()
        print "Update Level Surface Module with %d Level(s), range = [ %f, %f ], levels = %s" %  ( self.numberOfLevels, self.range[0], self.range[1], str(self.getLevelValues()) )  
                           
    def buildPipeline(self):
        """ execute() -> None
        Dispatch the vtkRenderer to the actual rendering widget
        """ 
        
        texture_ispec = self.getInputSpec(  1 )                
        xMin, xMax, yMin, yMax, zMin, zMax = self.input().GetWholeExtent()       
        self.sliceCenter = [ (xMax-xMin)/2, (yMax-yMin)/2, (zMax-zMin)/2  ]       
        spacing = self.input().GetSpacing()
        sx, sy, sz = spacing       
        origin = self.input().GetOrigin()
        ox, oy, oz = origin
        dataType = self.input().GetScalarTypeAsString()
        self.setMaxScalarValue( self.input().GetScalarType() )
        self.colorByMappedScalars = False
        rangeBounds = self.getRangeBounds()
        print "Data Type = %s, range = (%f,%f), max_scalar = %s" % ( dataType, rangeBounds[0], rangeBounds[1], self._max_scalar_value )

        dr = rangeBounds[1] - rangeBounds[0]
        range_offset = .2*dr
        self.range = [ rangeBounds[0] + range_offset, rangeBounds[1] - range_offset ]
        self.probeFilter = None
        textureRange = self.range
        if texture_ispec and texture_ispec.input:
            self.probeFilter = vtk.vtkProbeFilter()
            textureRange = texture_ispec.input.GetScalarRange()
            self.probeFilter.SetSource( texture_ispec.input )
            self.generateTexture = True
#        elif testTexture:
#            self.probeFilter = vtk.vtkProbeFilter()
#            textureGenerator = vtk.vtkImageSinusoidSource()
#            textureGenerator.SetWholeExtent ( xMin, xMax, yMin, yMax, zMin, zMax )
#            textureGenerator.SetDirection( 0.0, 0.0, 1.0 )
#            textureGenerator.SetPeriod( xMax-xMin )
#            textureGenerator.SetAmplitude( 125.0 )
#            textureGenerator.Update()
#                        
#            imageInfo = vtk.vtkImageChangeInformation()
#            imageInfo.SetInputConnection( textureGenerator.GetOutputPort() ) 
#            imageInfo.SetOutputOrigin( 0.0, 0.0, 0.0 )
#            imageInfo.SetOutputExtentStart( xMin, yMin, zMin )
#            imageInfo.SetOutputSpacing( spacing[0], spacing[1], spacing[2] )
#        
#            result = imageInfo.GetOutput() 
#            textureRange = result.GetScalarRange()           
#            self.probeFilter.SetSource( result )
            
#        if  textureRange <> None: print " Texture Range = %s " % str( textureRange )
        
#        vtkImageResample
#        shrinkFactor = 4
#        shrink = vtk.vtkImageShrink3D()
#        shrink.SetShrinkFactors(shrinkFactor, shrinkFactor, 1)
#        shrink.SetInputConnection(demModel.GetOutputPort())
#        shrink.AveragingOn()

#        self.levelSetFilter = vtk.vtkImageMarchingCubes()
        
        self.levelSetFilter = vtk.vtkContourFilter()
        self.inputModule().inputToAlgorithm( self.levelSetFilter )
        self.levelSetMapper = vtk.vtkPolyDataMapper()
        if ( self.probeFilter == None ):
            imageRange = self.getImageValues( self.range ) 
            self.levelSetMapper.SetInputConnection( self.levelSetFilter.GetOutputPort() ) 
            self.levelSetMapper.SetScalarRange( imageRange[0], imageRange[1] )
        else: 
            self.probeFilter.SetInputConnection( self.levelSetFilter.GetOutputPort() )
            self.levelSetMapper.SetInputConnection( self.probeFilter.GetOutputPort() ) 
            self.levelSetMapper.SetScalarRange( textureRange )
            
        if texture_ispec and texture_ispec.input:
            colormapManager = self.getColormapManager( index=1 )     
            colormapManager.setAlphaRange ( self.opacityRange ) 
            self.levelSetMapper.SetLookupTable( colormapManager.lut ) 
            self.levelSetMapper.SetColorModeToMapScalars()
            self.levelSetMapper.UseLookupTableScalarRangeOn()
        else:
            colormapManager = self.getColormapManager()     
            colormapManager.setAlphaRange ( self.opacityRange ) 
        
        self.updateLevels()
          
#        levelSetMapper.SetColorModeToMapScalars()  
#        levelSetActor = vtk.vtkLODActor() 
        levelSetActor = vtk.vtkActor() 
#            levelSetMapper.ScalarVisibilityOff() 
#            levelSetActor.SetProperty( self.levelSetProperty )              
        levelSetActor.SetMapper( self.levelSetMapper )
        
#        pointData = self.levelSetFilter.GetOutput().GetPointData()
#        pointData.SetScalars( colorLevelData )
        
#        if pd <> None:
#            na = pd.GetNumberOfArrays()
#            print " ** Dataset has %d arrays. ** " % ( pd.GetNumberOfArrays() )
#            for i in range( na ): print "   ---  Array %d: %s " % ( i,  str( pd.GetArrayName(i) ) )
#        else: print " ** No point data. "
           
        self.renderer.AddActor( levelSetActor )
        self.renderer.SetBackground( VTK_BACKGROUND_COLOR[0], VTK_BACKGROUND_COLOR[1], VTK_BACKGROUND_COLOR[2] ) 
        self.set3DOutput()                                              
                                                

class NLevelConfigurationWidget( IVModuleConfigurationDialog ):
    """
    NLevelConfigurationWidget ...   
    """    
    def __init__(self, name, **args):
        IVModuleConfigurationDialog.__init__( self, name, **args )
        
    @staticmethod   
    def getSignature():
        return [ (Integer, 'nlevels'), ]
        
    def getValue(self):
        return int( self.nLevelCombo.currentText() )

    def setValue( self, value ):
        nLevel = int( getItem( value ) )
        if nLevel > 0: self.nLevelCombo.setCurrentIndex( nLevel-1 )
        else: print>>sys.stderr, " Illegal number of levels: %s " % nLevel
        
    def createContent(self):
        nLevelTab = QWidget() 
        self.tabbedWidget.addTab( nLevelTab, 'Levels' )                                                     
        self.tabbedWidget.setCurrentWidget(nLevelTab)
        layout = QGridLayout()
        nLevelTab.setLayout( layout ) 
        layout.setMargin(10)
        layout.setSpacing(20)
       
        nLevel_label = QLabel( "Number of Levels:"  )
        layout.addWidget( nLevel_label, 0, 0 ) 

        self.nLevelCombo =  QComboBox ( self.parent() )
        nLevel_label.setBuddy( self.nLevelCombo )
        self.nLevelCombo.setMaximumHeight( 30 )
        layout.addWidget( self.nLevelCombo, 0,1 )
        for iLevel in range(1,6): self.nLevelCombo.addItem( str(iLevel) )   
        self.connect( self.nLevelCombo, SIGNAL("currentIndexChanged(QString)"), self.updateParameter )  


from packages.vtDV3D.WorkflowModule import WorkflowModule

class LevelSurface(WorkflowModule):
    
    PersistentModuleClass = PM_LevelSurface
    
    def __init__( self, **args ):
        WorkflowModule.__init__(self, **args) 
               
if __name__ == '__main__':
    executeVistrail( 'LevelSurfaceDemo' )
 

import os.path
import pandas as pd
import nrrd
from cip_python.classification.distance_feature_extractor \
  import DistanceFeatureExtractor
from cip_python.classification.kde_histogram_feature_extractor \
  import kdeHistExtractor  
import numpy as np
import pdb
from pandas.util.testing import assert_frame_equal

#from cip_python.input_output.image_reader_writer import ImageReaderWriter

#np.set_printoptions(precision = 3, suppress = True, threshold=1e6,
#                    linewidth=200) 

def test_execute():
    lm = np.ones([2, 2, 1])
    patches = np.ones([2, 2, 1])

    ct = np.ones([2, 2, 1])
    ct[0, 0, 0] = 5
    ct[0, 1, 0] = 7
    ct[1, 0, 0] = 6
    ct[1, 1, 0] = 8                
    
    dist_map = np.zeros([2, 2, 1])
    dist_map[0, 0, 0] = 1
    dist_map[0, 1, 0] = 2
    dist_map[1, 0, 0] = 3
    dist_map[1, 1, 0] = 4            
    
    dist_extractor = DistanceFeatureExtractor(chest_region="WholeLung")
    dist_extractor.fit(dist_map, lm, patches)

    hist_extractor = kdeHistExtractor(lower_limit=5, upper_limit=8)
    hist_extractor.fit(ct, lm, patches)

    hist_extractor2 = kdeHistExtractor(lower_limit=5, upper_limit=8, 
                                       in_df=dist_extractor.df_)
    hist_extractor2.fit(ct, lm, patches)

    dist_extractor2 = DistanceFeatureExtractor(chest_region="WholeLung",
                                               in_df=hist_extractor.df_)
    dist_extractor2.fit(dist_map, lm, patches)    

    assert dist_extractor2.df_.ix[0, 'patch_label'] == 1, \
      "patch_label not as expected"
    assert dist_extractor2.df_.ix[0, 'ChestRegion'] == 'UndefinedRegion', \
      "ChestRegion not as expected"
    assert dist_extractor2.df_.ix[0, 'ChestType'] == 'UndefinedType', \
      "ChestType not as expected"
    assert dist_extractor2.df_.ix[0, 'WholeLungDistance'] ==  2.5, \
      "WholeLungDistance not as expected"
    assert dist_extractor2.df_.ix[0, 'hu5'] == 0.23255479542667767, \
      "hu5 not as expected"
    assert dist_extractor2.df_.ix[0, 'hu6'] == 0.25565358411460765, \
      "hu6 not as expected"
    assert dist_extractor2.df_.ix[0, 'hu7'] == 0.25565358411460765, \
      "hu7 not as expected"
    assert dist_extractor2.df_.ix[0, 'hu8'] == 0.23255479542667767, \
      "hu8 not as expected"

    assert hist_extractor2.df_.ix[0, 'patch_label'] == 1, \
      "patch_label not as expected"
    assert hist_extractor2.df_.ix[0, 'ChestRegion'] == 'UndefinedRegion', \
      "ChestRegion not as expected"
    assert hist_extractor2.df_.ix[0, 'ChestType'] == 'UndefinedType', \
      "ChestType not as expected"
    assert hist_extractor2.df_.ix[0, 'WholeLungDistance'] ==  2.5, \
      "WholeLungDistance not as expected"
    assert hist_extractor2.df_.ix[0, 'hu5'] == 0.23255479542667767, \
      "hu5 not as expected"
    assert hist_extractor2.df_.ix[0, 'hu6'] == 0.25565358411460765, \
      "hu6 not as expected"
    assert hist_extractor2.df_.ix[0, 'hu7'] == 0.25565358411460765, \
      "hu7 not as expected"
    assert hist_extractor2.df_.ix[0, 'hu8'] == 0.23255479542667767, \
      "hu8 not as expected"      
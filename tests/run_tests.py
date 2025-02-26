# -*- coding: utf-8 -*-
# Copyright (c) 2004-2018 Wageningen Environmental Sciences, Wageningen-UR
# Allard de Wit (allard.dewit@wur.nl), January 2018
"""This runs the YAML unittests by processing the various YAML test file in the `test_data_dir`
"""
import unittest
import os
import glob

import yaml

from pcse.base.parameter_providers import ParameterProvider
from pcse.crop.phenology import DVS_Phenology
from pcse.crop.leaf_dynamics import WOFOST_Leaf_Dynamics
from pcse.crop.assimilation import WOFOST_Assimilation
from pcse.crop.respiration import WOFOST_Maintenance_Respiration
from pcse.crop.partitioning import DVS_Partitioning
from pcse.crop.root_dynamics import WOFOST_Root_Dynamics
from pcse.crop.evapotranspiration import Evapotranspiration
from pcse.crop.wofost import Wofost
from pcse.soil.classic_waterbalance import WaterbalanceFD
from .test_code import TestEngine, TestConfigurationLoader, TestWeatherDataProvider, TestSimulationObject

# This defines the YAML tests, each rows represents:
# - a pattern for searching the YAML tests within the test_data_dir
# - the crop simobject to be tested
# - an optional soil simobject to be tested
test_data_dir = os.path.join(os.path.dirname(__file__), "test_data")
quick_tests = [("test_potentialproduction_wofost71*", Wofost, None),
               ("test_waterlimitedproduction_wofost71*", Wofost, WaterbalanceFD)]
full_tests = [("test_phenology_wofost71*", DVS_Phenology, None),
              ("test_assimilation_wofost71*", WOFOST_Assimilation, None),
              ("test_partitioning_wofost71*", DVS_Partitioning, None),
              ("test_leafdynamics_wofost71*", WOFOST_Leaf_Dynamics, None),
              ("test_rootdynamics_wofost71*", WOFOST_Root_Dynamics, None),
              ("test_respiration_wofost71*", WOFOST_Maintenance_Respiration, None),
              ("test_transpiration_wofost71*", Evapotranspiration, None),
              ].extend(quick_tests)


class PCSETestCaseYAML(unittest.TestCase):
    """A Testcase template for a unit tests with YAML inputs.

    This will be subclassed dynamically (using type()) in order to populate the
    class attributes below.
    """
    YAML_test_input_fname = None
    crop_simobj = None
    soil_simobj = None

    def setUp(self):
        # Load YAML inputs
        inputs = yaml.safe_load(open(self.YAML_test_input_fname))

        # Prepare input categories for Engine
        self.reference_results = inputs["ModelResults"]
        self.precision = inputs["Precision"]
        external_states = inputs["ExternalStates"]
        agro = inputs["AgroManagement"]
        cropd = inputs["ModelParameters"]

        wdp = TestWeatherDataProvider(inputs["WeatherVariables"])
        params = ParameterProvider(cropdata=cropd)
        test_config = TestConfigurationLoader(inputs, self.crop_simobj, self.soil_simobj)
        engine = TestEngine(params, wdp, agro, test_config, external_states)
        engine.run_till_terminate()
        self.results = engine.get_output()

    def runTest(self):
        msg = ("Length of time-series of reference results [%i] not matching with length of "
               "timeseries of model output [%i]." % (len(self.reference_results), len(self.results)))
        self.assertEqual(len(self.reference_results), len(self.results), msg)

        for reference, model in zip(self.reference_results, self.results):
            self.assertEqual(reference["DAY"], model["day"], "Day not matching")
            for variable, precision in self.precision.items():
                ref_value = reference[variable]
                mod_value = model[variable]
                try:
                    self.assertTrue(abs(ref_value - mod_value) < precision,
                       "Variable '%s' not equal on day '%s': %f != %f" %
                       (variable, reference["DAY"], ref_value, mod_value))
                except TypeError as e:
                    if ref_value is None and mod_value is None:
                        pass
                    else:
                        raise


def suite(quick=True):
    suite = unittest.TestSuite()
    test_sets = quick_tests if quick else full_tests
    for pattern, crop_simobj, soil_simobj in test_sets:
        test_class_name = "Wrapped" + crop_simobj.__class__.__name__
        wrapped_simobj = type(test_class_name, (TestSimulationObject,),
                              {"test_class": crop_simobj})
        fnames = glob.glob(os.path.join(test_data_dir, pattern))
        for i, fname in enumerate(fnames):
            if quick and i % 10 != 0:
                    continue
            test_class = type(fname, (PCSETestCaseYAML,), {"YAML_test_input_fname": fname,
                                                           "crop_simobj": wrapped_simobj,
                                                           "soil_simobj": soil_simobj})
            suite.addTest(unittest.makeSuite(test_class))

    return suite


if __name__ == "__main__":
    unittest.TextTestRunner(verbosity=2).run(suite())


"""Tests for JMX Validator module."""

import xml.etree.ElementTree as ET
from pathlib import Path
from xml.dom import minidom

import pytest

from jmeter_gen.core.jmx_validator import JMXValidationException, JMXValidator


class TestJMXValidator:
    """Test suite for JMXValidator class."""

    @pytest.fixture
    def validator(self) -> JMXValidator:
        """Create a JMXValidator instance for testing.

        Returns:
            JMXValidator instance
        """
        return JMXValidator()

    @pytest.fixture
    def valid_jmx_content(self) -> str:
        """Create valid JMX file content for testing.

        Returns:
            Valid JMX XML string
        """
        return """<?xml version="1.0" encoding="UTF-8"?>
<jmeterTestPlan version="1.2" properties="5.0" jmeter="5.6">
  <hashTree>
    <TestPlan guiclass="TestPlanGui" testclass="TestPlan" testname="Test Plan" enabled="true">
      <stringProp name="TestPlan.comments"></stringProp>
      <boolProp name="TestPlan.functional_mode">false</boolProp>
      <boolProp name="TestPlan.serialize_threadgroups">false</boolProp>
      <elementProp name="TestPlan.user_defined_variables" elementType="Arguments">
        <collectionProp name="Arguments.arguments"/>
      </elementProp>
    </TestPlan>
    <hashTree>
      <ThreadGroup guiclass="ThreadGroupGui" testclass="ThreadGroup" testname="Thread Group" enabled="true">
        <stringProp name="ThreadGroup.on_sample_error">continue</stringProp>
        <elementProp name="ThreadGroup.main_controller" elementType="LoopController">
          <boolProp name="LoopController.continue_forever">false</boolProp>
          <stringProp name="LoopController.loops">1</stringProp>
        </elementProp>
        <stringProp name="ThreadGroup.num_threads">10</stringProp>
        <stringProp name="ThreadGroup.ramp_time">5</stringProp>
        <boolProp name="ThreadGroup.scheduler">true</boolProp>
        <stringProp name="ThreadGroup.duration">60</stringProp>
        <stringProp name="ThreadGroup.delay">0</stringProp>
      </ThreadGroup>
      <hashTree>
        <ConfigTestElement guiclass="HttpDefaultsGui" testclass="ConfigTestElement" testname="HTTP Request Defaults" enabled="true">
          <stringProp name="HTTPSampler.domain">localhost</stringProp>
          <stringProp name="HTTPSampler.port">8080</stringProp>
          <stringProp name="HTTPSampler.protocol">http</stringProp>
        </ConfigTestElement>
        <hashTree/>
        <HTTPSamplerProxy guiclass="HttpTestSampleGui" testclass="HTTPSamplerProxy" testname="GET /api/users" enabled="true">
          <elementProp name="HTTPsampler.Arguments" elementType="Arguments">
            <collectionProp name="Arguments.arguments"/>
          </elementProp>
          <stringProp name="HTTPSampler.domain"></stringProp>
          <stringProp name="HTTPSampler.port"></stringProp>
          <stringProp name="HTTPSampler.protocol"></stringProp>
          <stringProp name="HTTPSampler.path">/api/users</stringProp>
          <stringProp name="HTTPSampler.method">GET</stringProp>
          <boolProp name="HTTPSampler.follow_redirects">true</boolProp>
          <boolProp name="HTTPSampler.use_keepalive">true</boolProp>
        </HTTPSamplerProxy>
        <hashTree>
          <ResponseAssertion guiclass="AssertionGui" testclass="ResponseAssertion" testname="Assert 200" enabled="true">
            <collectionProp name="Asserion.test_strings">
              <stringProp name="49586">200</stringProp>
            </collectionProp>
            <stringProp name="Assertion.test_field">Assertion.response_code</stringProp>
            <intProp name="Assertion.test_type">8</intProp>
          </ResponseAssertion>
          <hashTree/>
        </hashTree>
      </hashTree>
    </hashTree>
  </hashTree>
</jmeterTestPlan>
"""

    @pytest.fixture
    def valid_jmx_file(self, tmp_path: Path, valid_jmx_content: str) -> Path:
        """Create a valid temporary JMX file for testing.

        Args:
            tmp_path: Pytest temporary directory fixture
            valid_jmx_content: Valid JMX content fixture

        Returns:
            Path to temporary JMX file
        """
        jmx_file = tmp_path / "valid_test.jmx"
        jmx_file.write_text(valid_jmx_content)
        return jmx_file

    def test_validate_valid_jmx(self, validator: JMXValidator, valid_jmx_file: Path):
        """Test validation of a valid JMX file.

        Args:
            validator: JMXValidator fixture
            valid_jmx_file: Valid JMX file fixture
        """
        result = validator.validate(str(valid_jmx_file))

        assert result["valid"] is True
        assert len(result["issues"]) == 0
        assert isinstance(result["recommendations"], list)

    def test_validate_nonexistent_file(self, validator: JMXValidator):
        """Test validation of nonexistent file raises FileNotFoundError.

        Args:
            validator: JMXValidator fixture
        """
        with pytest.raises(FileNotFoundError):
            validator.validate("/nonexistent/path/test.jmx")

    def test_validate_invalid_xml(self, validator: JMXValidator, tmp_path: Path):
        """Test validation of invalid XML raises JMXValidationException.

        Args:
            validator: JMXValidator fixture
            tmp_path: Pytest temporary directory fixture
        """
        invalid_jmx = tmp_path / "invalid.jmx"
        invalid_jmx.write_text("<?xml version='1.0'?><invalid>")

        with pytest.raises(JMXValidationException):
            validator.validate(str(invalid_jmx))

    def test_validate_missing_test_plan(self, validator: JMXValidator, tmp_path: Path):
        """Test validation detects missing TestPlan element.

        Args:
            validator: JMXValidator fixture
            tmp_path: Pytest temporary directory fixture
        """
        jmx_content = """<?xml version="1.0" encoding="UTF-8"?>
<jmeterTestPlan version="1.2" properties="5.0">
  <hashTree>
    <ThreadGroup guiclass="ThreadGroupGui" testclass="ThreadGroup" testname="Thread Group">
      <stringProp name="ThreadGroup.num_threads">10</stringProp>
    </ThreadGroup>
  </hashTree>
</jmeterTestPlan>
"""
        jmx_file = tmp_path / "no_testplan.jmx"
        jmx_file.write_text(jmx_content)

        result = validator.validate(str(jmx_file))

        assert result["valid"] is False
        assert "Missing TestPlan element" in result["issues"]

    def test_validate_missing_thread_group(self, validator: JMXValidator, tmp_path: Path):
        """Test validation detects missing ThreadGroup element.

        Args:
            validator: JMXValidator fixture
            tmp_path: Pytest temporary directory fixture
        """
        jmx_content = """<?xml version="1.0" encoding="UTF-8"?>
<jmeterTestPlan version="1.2" properties="5.0">
  <hashTree>
    <TestPlan guiclass="TestPlanGui" testclass="TestPlan" testname="Test Plan">
      <boolProp name="TestPlan.functional_mode">false</boolProp>
    </TestPlan>
    <hashTree/>
  </hashTree>
</jmeterTestPlan>
"""
        jmx_file = tmp_path / "no_threadgroup.jmx"
        jmx_file.write_text(jmx_content)

        result = validator.validate(str(jmx_file))

        assert result["valid"] is False
        assert "Missing ThreadGroup element" in result["issues"]

    def test_validate_wrong_root_element(self, validator: JMXValidator, tmp_path: Path):
        """Test validation detects wrong root element.

        Args:
            validator: JMXValidator fixture
            tmp_path: Pytest temporary directory fixture
        """
        jmx_content = """<?xml version="1.0" encoding="UTF-8"?>
<wrongRoot version="1.2">
  <hashTree/>
</wrongRoot>
"""
        jmx_file = tmp_path / "wrong_root.jmx"
        jmx_file.write_text(jmx_content)

        result = validator.validate(str(jmx_file))

        assert result["valid"] is False
        assert "Root element must be 'jmeterTestPlan'" in result["issues"]

    def test_validate_missing_hashtree(self, validator: JMXValidator, tmp_path: Path):
        """Test validation detects missing main hashTree element.

        Args:
            validator: JMXValidator fixture
            tmp_path: Pytest temporary directory fixture
        """
        jmx_content = """<?xml version="1.0" encoding="UTF-8"?>
<jmeterTestPlan version="1.2" properties="5.0">
  <TestPlan/>
</jmeterTestPlan>
"""
        jmx_file = tmp_path / "no_hashtree.jmx"
        jmx_file.write_text(jmx_content)

        result = validator.validate(str(jmx_file))

        assert result["valid"] is False
        assert "Missing main hashTree element after jmeterTestPlan" in result["issues"]

    def test_validate_missing_num_threads(self, validator: JMXValidator, tmp_path: Path):
        """Test validation detects missing num_threads configuration.

        Args:
            validator: JMXValidator fixture
            tmp_path: Pytest temporary directory fixture
        """
        jmx_content = """<?xml version="1.0" encoding="UTF-8"?>
<jmeterTestPlan version="1.2" properties="5.0">
  <hashTree>
    <TestPlan guiclass="TestPlanGui" testclass="TestPlan" testname="Test Plan"/>
    <hashTree>
      <ThreadGroup guiclass="ThreadGroupGui" testclass="ThreadGroup" testname="Thread Group">
        <stringProp name="ThreadGroup.ramp_time">5</stringProp>
        <boolProp name="ThreadGroup.scheduler">true</boolProp>
        <stringProp name="ThreadGroup.duration">60</stringProp>
      </ThreadGroup>
      <hashTree/>
    </hashTree>
  </hashTree>
</jmeterTestPlan>
"""
        jmx_file = tmp_path / "no_threads.jmx"
        jmx_file.write_text(jmx_content)

        result = validator.validate(str(jmx_file))

        assert result["valid"] is False
        assert "ThreadGroup missing 'num_threads' configuration" in result["issues"]

    def test_validate_zero_threads(self, validator: JMXValidator, tmp_path: Path):
        """Test validation detects invalid num_threads value.

        Args:
            validator: JMXValidator fixture
            tmp_path: Pytest temporary directory fixture
        """
        jmx_content = """<?xml version="1.0" encoding="UTF-8"?>
<jmeterTestPlan version="1.2" properties="5.0">
  <hashTree>
    <TestPlan guiclass="TestPlanGui" testclass="TestPlan" testname="Test Plan"/>
    <hashTree>
      <ThreadGroup guiclass="ThreadGroupGui" testclass="ThreadGroup" testname="Thread Group">
        <stringProp name="ThreadGroup.num_threads">0</stringProp>
        <stringProp name="ThreadGroup.ramp_time">5</stringProp>
        <boolProp name="ThreadGroup.scheduler">true</boolProp>
        <stringProp name="ThreadGroup.duration">60</stringProp>
      </ThreadGroup>
      <hashTree/>
    </hashTree>
  </hashTree>
</jmeterTestPlan>
"""
        jmx_file = tmp_path / "zero_threads.jmx"
        jmx_file.write_text(jmx_content)

        result = validator.validate(str(jmx_file))

        assert result["valid"] is False
        assert any("num_threads' must be > 0" in issue for issue in result["issues"])

    def test_validate_invalid_num_threads(self, validator: JMXValidator, tmp_path: Path):
        """Test validation detects non-numeric num_threads value.

        Args:
            validator: JMXValidator fixture
            tmp_path: Pytest temporary directory fixture
        """
        jmx_content = """<?xml version="1.0" encoding="UTF-8"?>
<jmeterTestPlan version="1.2" properties="5.0">
  <hashTree>
    <TestPlan guiclass="TestPlanGui" testclass="TestPlan" testname="Test Plan"/>
    <hashTree>
      <ThreadGroup guiclass="ThreadGroupGui" testclass="ThreadGroup" testname="Thread Group">
        <stringProp name="ThreadGroup.num_threads">invalid</stringProp>
        <stringProp name="ThreadGroup.ramp_time">5</stringProp>
      </ThreadGroup>
      <hashTree/>
    </hashTree>
  </hashTree>
</jmeterTestPlan>
"""
        jmx_file = tmp_path / "invalid_threads.jmx"
        jmx_file.write_text(jmx_content)

        result = validator.validate(str(jmx_file))

        assert result["valid"] is False
        assert any("must be a valid number" in issue for issue in result["issues"])

    def test_validate_missing_ramp_time(self, validator: JMXValidator, tmp_path: Path):
        """Test validation detects missing ramp_time configuration.

        Args:
            validator: JMXValidator fixture
            tmp_path: Pytest temporary directory fixture
        """
        jmx_content = """<?xml version="1.0" encoding="UTF-8"?>
<jmeterTestPlan version="1.2" properties="5.0">
  <hashTree>
    <TestPlan guiclass="TestPlanGui" testclass="TestPlan" testname="Test Plan"/>
    <hashTree>
      <ThreadGroup guiclass="ThreadGroupGui" testclass="ThreadGroup" testname="Thread Group">
        <stringProp name="ThreadGroup.num_threads">10</stringProp>
        <boolProp name="ThreadGroup.scheduler">true</boolProp>
        <stringProp name="ThreadGroup.duration">60</stringProp>
      </ThreadGroup>
      <hashTree/>
    </hashTree>
  </hashTree>
</jmeterTestPlan>
"""
        jmx_file = tmp_path / "no_ramptime.jmx"
        jmx_file.write_text(jmx_content)

        result = validator.validate(str(jmx_file))

        assert result["valid"] is False
        assert "ThreadGroup missing 'ramp_time' configuration" in result["issues"]

    def test_validate_missing_duration_control(self, validator: JMXValidator, tmp_path: Path):
        """Test validation detects missing duration control (scheduler or loops).

        Args:
            validator: JMXValidator fixture
            tmp_path: Pytest temporary directory fixture
        """
        jmx_content = """<?xml version="1.0" encoding="UTF-8"?>
<jmeterTestPlan version="1.2" properties="5.0">
  <hashTree>
    <TestPlan guiclass="TestPlanGui" testclass="TestPlan" testname="Test Plan"/>
    <hashTree>
      <ThreadGroup guiclass="ThreadGroupGui" testclass="ThreadGroup" testname="Thread Group">
        <stringProp name="ThreadGroup.num_threads">10</stringProp>
        <stringProp name="ThreadGroup.ramp_time">5</stringProp>
      </ThreadGroup>
      <hashTree/>
    </hashTree>
  </hashTree>
</jmeterTestPlan>
"""
        jmx_file = tmp_path / "no_duration.jmx"
        jmx_file.write_text(jmx_content)

        result = validator.validate(str(jmx_file))

        assert result["valid"] is False
        assert any("scheduler enabled or loop count" in issue for issue in result["issues"])

    def test_validate_scheduler_without_duration(self, validator: JMXValidator, tmp_path: Path):
        """Test validation detects scheduler enabled without duration.

        Args:
            validator: JMXValidator fixture
            tmp_path: Pytest temporary directory fixture
        """
        jmx_content = """<?xml version="1.0" encoding="UTF-8"?>
<jmeterTestPlan version="1.2" properties="5.0">
  <hashTree>
    <TestPlan guiclass="TestPlanGui" testclass="TestPlan" testname="Test Plan"/>
    <hashTree>
      <ThreadGroup guiclass="ThreadGroupGui" testclass="ThreadGroup" testname="Thread Group">
        <stringProp name="ThreadGroup.num_threads">10</stringProp>
        <stringProp name="ThreadGroup.ramp_time">5</stringProp>
        <boolProp name="ThreadGroup.scheduler">true</boolProp>
      </ThreadGroup>
      <hashTree/>
    </hashTree>
  </hashTree>
</jmeterTestPlan>
"""
        jmx_file = tmp_path / "scheduler_no_duration.jmx"
        jmx_file.write_text(jmx_content)

        result = validator.validate(str(jmx_file))

        assert result["valid"] is False
        assert any("scheduler enabled but missing 'duration'" in issue for issue in result["issues"])

    def test_validate_no_samplers(self, validator: JMXValidator, tmp_path: Path):
        """Test validation detects no HTTP samplers.

        Args:
            validator: JMXValidator fixture
            tmp_path: Pytest temporary directory fixture
        """
        jmx_content = """<?xml version="1.0" encoding="UTF-8"?>
<jmeterTestPlan version="1.2" properties="5.0">
  <hashTree>
    <TestPlan guiclass="TestPlanGui" testclass="TestPlan" testname="Test Plan"/>
    <hashTree>
      <ThreadGroup guiclass="ThreadGroupGui" testclass="ThreadGroup" testname="Thread Group">
        <stringProp name="ThreadGroup.num_threads">10</stringProp>
        <stringProp name="ThreadGroup.ramp_time">5</stringProp>
        <boolProp name="ThreadGroup.scheduler">true</boolProp>
        <stringProp name="ThreadGroup.duration">60</stringProp>
      </ThreadGroup>
      <hashTree/>
    </hashTree>
  </hashTree>
</jmeterTestPlan>
"""
        jmx_file = tmp_path / "no_samplers.jmx"
        jmx_file.write_text(jmx_content)

        result = validator.validate(str(jmx_file))

        assert result["valid"] is False
        assert "No HTTP samplers found in test plan" in result["issues"]

    def test_validate_sampler_missing_path(self, validator: JMXValidator, tmp_path: Path):
        """Test validation detects sampler missing path.

        Args:
            validator: JMXValidator fixture
            tmp_path: Pytest temporary directory fixture
        """
        jmx_content = """<?xml version="1.0" encoding="UTF-8"?>
<jmeterTestPlan version="1.2" properties="5.0">
  <hashTree>
    <TestPlan guiclass="TestPlanGui" testclass="TestPlan" testname="Test Plan"/>
    <hashTree>
      <ThreadGroup guiclass="ThreadGroupGui" testclass="ThreadGroup" testname="Thread Group">
        <stringProp name="ThreadGroup.num_threads">10</stringProp>
        <stringProp name="ThreadGroup.ramp_time">5</stringProp>
        <boolProp name="ThreadGroup.scheduler">true</boolProp>
        <stringProp name="ThreadGroup.duration">60</stringProp>
      </ThreadGroup>
      <hashTree>
        <HTTPSamplerProxy guiclass="HttpTestSampleGui" testclass="HTTPSamplerProxy" testname="Test Sampler">
          <stringProp name="HTTPSampler.method">GET</stringProp>
          <stringProp name="HTTPSampler.domain">localhost</stringProp>
        </HTTPSamplerProxy>
        <hashTree/>
      </hashTree>
    </hashTree>
  </hashTree>
</jmeterTestPlan>
"""
        jmx_file = tmp_path / "no_path.jmx"
        jmx_file.write_text(jmx_content)

        result = validator.validate(str(jmx_file))

        assert result["valid"] is False
        assert any("missing path configuration" in issue for issue in result["issues"])

    def test_validate_sampler_missing_method(self, validator: JMXValidator, tmp_path: Path):
        """Test validation detects sampler missing HTTP method.

        Args:
            validator: JMXValidator fixture
            tmp_path: Pytest temporary directory fixture
        """
        jmx_content = """<?xml version="1.0" encoding="UTF-8"?>
<jmeterTestPlan version="1.2" properties="5.0">
  <hashTree>
    <TestPlan guiclass="TestPlanGui" testclass="TestPlan" testname="Test Plan"/>
    <hashTree>
      <ThreadGroup guiclass="ThreadGroupGui" testclass="ThreadGroup" testname="Thread Group">
        <stringProp name="ThreadGroup.num_threads">10</stringProp>
        <stringProp name="ThreadGroup.ramp_time">5</stringProp>
        <boolProp name="ThreadGroup.scheduler">true</boolProp>
        <stringProp name="ThreadGroup.duration">60</stringProp>
      </ThreadGroup>
      <hashTree>
        <HTTPSamplerProxy guiclass="HttpTestSampleGui" testclass="HTTPSamplerProxy" testname="Test Sampler">
          <stringProp name="HTTPSampler.path">/api/test</stringProp>
          <stringProp name="HTTPSampler.domain">localhost</stringProp>
        </HTTPSamplerProxy>
        <hashTree/>
      </hashTree>
    </hashTree>
  </hashTree>
</jmeterTestPlan>
"""
        jmx_file = tmp_path / "no_method.jmx"
        jmx_file.write_text(jmx_content)

        result = validator.validate(str(jmx_file))

        assert result["valid"] is False
        assert any("missing HTTP method" in issue for issue in result["issues"])

    def test_validate_sampler_no_domain_no_defaults(self, validator: JMXValidator, tmp_path: Path):
        """Test validation detects sampler with no domain and no defaults.

        Args:
            validator: JMXValidator fixture
            tmp_path: Pytest temporary directory fixture
        """
        jmx_content = """<?xml version="1.0" encoding="UTF-8"?>
<jmeterTestPlan version="1.2" properties="5.0">
  <hashTree>
    <TestPlan guiclass="TestPlanGui" testclass="TestPlan" testname="Test Plan"/>
    <hashTree>
      <ThreadGroup guiclass="ThreadGroupGui" testclass="ThreadGroup" testname="Thread Group">
        <stringProp name="ThreadGroup.num_threads">10</stringProp>
        <stringProp name="ThreadGroup.ramp_time">5</stringProp>
        <boolProp name="ThreadGroup.scheduler">true</boolProp>
        <stringProp name="ThreadGroup.duration">60</stringProp>
      </ThreadGroup>
      <hashTree>
        <HTTPSamplerProxy guiclass="HttpTestSampleGui" testclass="HTTPSamplerProxy" testname="Test Sampler">
          <stringProp name="HTTPSampler.path">/api/test</stringProp>
          <stringProp name="HTTPSampler.method">GET</stringProp>
          <stringProp name="HTTPSampler.domain"></stringProp>
        </HTTPSamplerProxy>
        <hashTree/>
      </hashTree>
    </hashTree>
  </hashTree>
</jmeterTestPlan>
"""
        jmx_file = tmp_path / "no_domain_no_defaults.jmx"
        jmx_file.write_text(jmx_content)

        result = validator.validate(str(jmx_file))

        assert result["valid"] is False
        assert any("no domain and no HTTP Request Defaults" in issue for issue in result["issues"])

    def test_recommendations_csv_config(self, validator: JMXValidator, valid_jmx_file: Path):
        """Test recommendations suggest CSV Data Set Config.

        Args:
            validator: JMXValidator fixture
            valid_jmx_file: Valid JMX file fixture
        """
        result = validator.validate(str(valid_jmx_file))

        assert any("CSV Data Set Config" in rec for rec in result["recommendations"])

    def test_recommendations_listeners(self, validator: JMXValidator, valid_jmx_file: Path):
        """Test recommendations suggest listeners.

        Args:
            validator: JMXValidator fixture
            valid_jmx_file: Valid JMX file fixture
        """
        result = validator.validate(str(valid_jmx_file))

        assert any("listeners" in rec for rec in result["recommendations"])

    def test_recommendations_timers(self, validator: JMXValidator, valid_jmx_file: Path):
        """Test recommendations suggest timers.

        Args:
            validator: JMXValidator fixture
            valid_jmx_file: Valid JMX file fixture
        """
        result = validator.validate(str(valid_jmx_file))

        assert any("timers" in rec for rec in result["recommendations"])

    def test_recommendations_duration_assertions(self, validator: JMXValidator, valid_jmx_file: Path):
        """Test recommendations suggest duration assertions.

        Args:
            validator: JMXValidator fixture
            valid_jmx_file: Valid JMX file fixture
        """
        result = validator.validate(str(valid_jmx_file))

        assert any("Duration Assertion" in rec for rec in result["recommendations"])

    def test_recommendations_low_thread_count(self, validator: JMXValidator, tmp_path: Path):
        """Test recommendations detect low thread count.

        Args:
            validator: JMXValidator fixture
            tmp_path: Pytest temporary directory fixture
        """
        jmx_content = """<?xml version="1.0" encoding="UTF-8"?>
<jmeterTestPlan version="1.2" properties="5.0">
  <hashTree>
    <TestPlan guiclass="TestPlanGui" testclass="TestPlan" testname="Test Plan"/>
    <hashTree>
      <ThreadGroup guiclass="ThreadGroupGui" testclass="ThreadGroup" testname="Thread Group">
        <stringProp name="ThreadGroup.num_threads">5</stringProp>
        <stringProp name="ThreadGroup.ramp_time">1</stringProp>
        <boolProp name="ThreadGroup.scheduler">true</boolProp>
        <stringProp name="ThreadGroup.duration">60</stringProp>
      </ThreadGroup>
      <hashTree>
        <ConfigTestElement guiclass="HttpDefaultsGui" testclass="ConfigTestElement" testname="HTTP Request Defaults">
          <stringProp name="HTTPSampler.domain">localhost</stringProp>
        </ConfigTestElement>
        <hashTree/>
        <HTTPSamplerProxy guiclass="HttpTestSampleGui" testclass="HTTPSamplerProxy" testname="Test">
          <stringProp name="HTTPSampler.path">/test</stringProp>
          <stringProp name="HTTPSampler.method">GET</stringProp>
        </HTTPSamplerProxy>
        <hashTree/>
      </hashTree>
    </hashTree>
  </hashTree>
</jmeterTestPlan>
"""
        jmx_file = tmp_path / "low_threads.jmx"
        jmx_file.write_text(jmx_content)

        result = validator.validate(str(jmx_file))

        assert result["valid"] is True
        assert any("Thread count is low" in rec for rec in result["recommendations"])

    def test_validate_with_loops_no_scheduler(self, validator: JMXValidator, tmp_path: Path):
        """Test validation succeeds with loops configured instead of scheduler.

        Args:
            validator: JMXValidator fixture
            tmp_path: Pytest temporary directory fixture
        """
        jmx_content = """<?xml version="1.0" encoding="UTF-8"?>
<jmeterTestPlan version="1.2" properties="5.0">
  <hashTree>
    <TestPlan guiclass="TestPlanGui" testclass="TestPlan" testname="Test Plan"/>
    <hashTree>
      <ThreadGroup guiclass="ThreadGroupGui" testclass="ThreadGroup" testname="Thread Group">
        <stringProp name="ThreadGroup.num_threads">10</stringProp>
        <stringProp name="ThreadGroup.ramp_time">5</stringProp>
        <elementProp name="ThreadGroup.main_controller" elementType="LoopController">
          <stringProp name="LoopController.loops">100</stringProp>
        </elementProp>
      </ThreadGroup>
      <hashTree>
        <ConfigTestElement guiclass="HttpDefaultsGui" testclass="ConfigTestElement" testname="HTTP Request Defaults">
          <stringProp name="HTTPSampler.domain">localhost</stringProp>
        </ConfigTestElement>
        <hashTree/>
        <HTTPSamplerProxy guiclass="HttpTestSampleGui" testclass="HTTPSamplerProxy" testname="Test">
          <stringProp name="HTTPSampler.path">/test</stringProp>
          <stringProp name="HTTPSampler.method">GET</stringProp>
        </HTTPSamplerProxy>
        <hashTree/>
      </hashTree>
    </hashTree>
  </hashTree>
</jmeterTestPlan>
"""
        jmx_file = tmp_path / "with_loops.jmx"
        jmx_file.write_text(jmx_content)

        result = validator.validate(str(jmx_file))

        assert result["valid"] is True
        # Should not have scheduler/loops issue
        assert not any("scheduler enabled or loop count" in issue for issue in result["issues"])

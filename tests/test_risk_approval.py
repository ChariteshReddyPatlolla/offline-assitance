import pytest
from agent_os.core.permissions import RiskClassifier, RiskLevel, PermissionManager, ApprovalEngine

def test_risk_classifier_low():
    assert RiskClassifier.evaluate("read_file", {}) == RiskLevel.LOW
    assert RiskClassifier.evaluate("create_file", {}) == RiskLevel.LOW
    assert RiskClassifier.evaluate("shell", {"command": "ls -la"}) == RiskLevel.LOW

def test_risk_classifier_medium():
    assert RiskClassifier.evaluate("shell", {"command": "npm install express"}) == RiskLevel.MEDIUM
    assert RiskClassifier.evaluate("write_file", {}) == RiskLevel.MEDIUM

def test_risk_classifier_high():
    assert RiskClassifier.evaluate("delete_file", {}) == RiskLevel.HIGH
    assert RiskClassifier.evaluate("shell", {"command": "rm -rf /tmp/dir"}) == RiskLevel.HIGH
    assert RiskClassifier.evaluate("kill_process", {"command": "kill 1234"}) == RiskLevel.HIGH

def test_risk_classifier_critical():
    assert RiskClassifier.evaluate("send_email", {}) == RiskLevel.CRITICAL
    assert RiskClassifier.evaluate("shell", {"command": "sudo apt-get install"}) == RiskLevel.CRITICAL

@pytest.mark.asyncio
async def test_permission_manager():
    manager = PermissionManager()
    engine = ApprovalEngine(manager)
    
    # 1. LOW Auto-approves
    res1 = manager.check_permission("read_file", {})
    assert res1["allowed"] is True
    
    # 2. HIGH Requires approval
    res2 = manager.check_permission("delete_file", {"path": "test.txt"})
    assert res2["allowed"] is False
    assert res2["risk"] == RiskLevel.HIGH
    
    # 3. Simulate user approval
    is_approved = engine.process_user_response("yes", res2["scope"])
    assert is_approved is True
    
    # 4. Check cache (should be allowed now)
    res3 = manager.check_permission("delete_file", {"path": "test.txt"})
    assert res3["allowed"] is True

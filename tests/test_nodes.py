import pytest

from netlogger import ami, config


def test_node_validation():
    assert ami.valid_node("41234") and ami.valid_node("2000") and not ami.valid_node("12")
    assert not ami.valid_node("41234; rpt restart") and not ami.valid_node("")


def test_connect_is_monitor_only_and_disconnect(fake_ami):
    ami.connect("41234")
    assert fake_ami.commands[-1] == "rpt cmd 1999 ilink 2 41234"  # 2 = monitor, never transceive
    assert [l["node"] for l in ami.links()] == ["41234"]
    ami.disconnect("41234")
    assert fake_ami.commands[-1] == "rpt cmd 1999 ilink 1 41234"
    assert ami.links() == []


def test_old_style_command_output(fake_ami):
    fake_ami.new_style = False
    fake_ami.links = ["2000"]
    links = ami.links()
    assert links[0]["node"] == "2000" and links[0]["state"] == "ESTABLISHED"


def test_bad_secret(fake_ami, monkeypatch):
    monkeypatch.setattr(config, "AMI_SECRET", "wrong")
    with pytest.raises(ami.AMIError, match="rejected"):
        ami.links()


def test_unreachable(monkeypatch):
    monkeypatch.setattr(config, "NODE_CONTROL", True)
    monkeypatch.setattr(config, "AMI_HOST", "127.0.0.1")
    monkeypatch.setattr(config, "AMI_PORT", 1)
    with pytest.raises(ami.AMIError, match="reach"):
        ami.links()


def test_node_api(admin, fake_ami):
    code, body = admin.get("/api/nodes")
    assert body["enabled"] and body["logger_node"] == "1999" and body["links"] == []
    assert admin.post("/api/nodes/connect", {"node": "41234"})[0] == 200
    assert [l["node"] for l in admin.get("/api/nodes")[1]["links"]] == ["41234"]
    assert admin.post("/api/nodes/connect", {"node": "1; rpt restart"})[0] == 400
    assert admin.post("/api/nodes/disconnect", {"node": "41234"})[0] == 200
    assert admin.get("/api/nodes")[1]["links"] == []


def test_node_api_off(admin, monkeypatch):
    monkeypatch.setattr(config, "NODE_CONTROL", False)
    assert admin.get("/api/nodes")[1]["enabled"] is False
    assert admin.post("/api/nodes/connect", {"node": "41234"})[0] == 400

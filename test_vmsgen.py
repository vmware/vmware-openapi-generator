import sys
import vmsgen

def test_tags_generation_from_short_name():
    expected = ['']
    actual = vmsgen.tags_from_service_name('three.levels.deep')
    assert expected == actual

def test_tags_generation_from_proper_name():
    expected = ['levels_deep']
    actual = vmsgen.tags_from_service_name('more.than.three.levels.deep')
    assert expected == actual

def test_default_ssl_security_option(monkeypatch):
    with monkeypatch.context() as m:
         expected = True
         m.setattr(sys, 'argv', ['a', '-vc', 'b'])
         _, _, _, actual = vmsgen.get_input_params()
         assert expected == actual

def test_setting_insecure_ssl_security_option(monkeypatch):
    with monkeypatch.context() as m:
         expected = False
         m.setattr(sys, 'argv', ['a', '-vc', 'b', '-k'])
         _, _, _, actual = vmsgen.get_input_params()
         assert expected == actual

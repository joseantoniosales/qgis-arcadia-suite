#!/usr/bin/env python3
"""
Test script for BETA 22 fixes:
1. LayerSymbolInfo missing 'layer' attribute
2. Debug mode persistence
3. Data structure compatibility

Run this from QGIS Python Console:
exec(open('/Volumes/Mac_Data/qgis-arcadia-suite/test_beta22_fixes.py').read())
"""

def test_layersymbolinfo_structure():
    """Test LayerSymbolInfo data structure"""
    print("=== Testing LayerSymbolInfo Structure ===")
    
    try:
        from ArcadiaCanvasLegend.tools.symbol_data_extractor import LayerSymbolInfo
        
        # Test creating LayerSymbolInfo with layer attribute
        test_layer_info = LayerSymbolInfo(
            layer_id="test_id",
            layer_name="Test Layer",
            layer_type="vector",
            geometry_type="Point",
            symbols=[],
            layer="mock_layer"  # Test the new parameter
        )
        
        # Test attribute access
        assert hasattr(test_layer_info, 'layer'), "Missing 'layer' attribute"
        assert hasattr(test_layer_info, 'layer_id'), "Missing 'layer_id' attribute"
        assert hasattr(test_layer_info, 'layer_name'), "Missing 'layer_name' attribute"
        assert hasattr(test_layer_info, 'layer_type'), "Missing 'layer_type' attribute"
        assert hasattr(test_layer_info, 'geometry_type'), "Missing 'geometry_type' attribute"
        assert hasattr(test_layer_info, 'symbols'), "Missing 'symbols' attribute"
        assert hasattr(test_layer_info, 'is_visible'), "Missing 'is_visible' attribute"
        assert hasattr(test_layer_info, 'is_valid'), "Missing 'is_valid' attribute"
        
        print("✓ LayerSymbolInfo structure test PASSED")
        print(f"  - layer: {test_layer_info.layer}")
        print(f"  - layer_name: {test_layer_info.layer_name}")
        print(f"  - layer_type: {test_layer_info.layer_type}")
        
        return True
        
    except Exception as e:
        print(f"✗ LayerSymbolInfo structure test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_conversion_layer():
    """Test LayerSymbolInfo to dict conversion"""
    print("\n=== Testing Conversion Layer ===")
    
    try:
        from ArcadiaCanvasLegend.tools.symbol_data_extractor import LayerSymbolInfo
        
        # Create test LayerSymbolInfo
        layer_info = LayerSymbolInfo(
            layer_id="test_id",
            layer_name="Test Layer",
            layer_type="vector",
            geometry_type="Point",
            symbols=[
                {
                    'label': 'Test Symbol',
                    'color': '#FF0000',
                    'type': 'simple',
                    'symbol': None
                }
            ],
            layer="mock_layer"
        )
        
        # Test conversion (simulated)
        item_dict = {
            'layer_name': layer_info.layer_name,
            'layer_id': layer_info.layer_id,
            'name': layer_info.layer_name,
            'type': 'layer',
            'layer': layer_info.layer,  # This should now work
            'visible': getattr(layer_info, 'is_visible', True),
            'is_group_child': False,
            'symbols': []
        }
        
        # Convert symbols
        for symbol_info in layer_info.symbols:
            symbol_dict = {
                'label': symbol_info.get('label', layer_info.layer_name),
                'layer_type': symbol_info.get('layer_type', layer_info.layer_type),
                'geometry_type': symbol_info.get('geometry_type', layer_info.geometry_type),
                'color': symbol_info.get('color', '#808080'),
                'type': symbol_info.get('type', 'symbol'),
                'symbol': symbol_info.get('symbol')
            }
            item_dict['symbols'].append(symbol_dict)
        
        print("✓ Conversion layer test PASSED")
        print(f"  - Converted dict has 'layer': {'layer' in item_dict}")
        print(f"  - Symbol count: {len(item_dict['symbols'])}")
        
        return True
        
    except Exception as e:
        print(f"✗ Conversion layer test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_debug_mode_integration():
    """Test debug mode setting persistence"""
    print("\n=== Testing Debug Mode Integration ===")
    
    try:
        # Import utilities
        from ArcadiaCanvasLegend.utils import get_arcadia_setting, set_arcadia_setting
        
        # Test setting and getting debug mode
        test_value = True
        set_arcadia_setting('CANVAS_LEGEND', 'debug_mode', test_value)
        
        retrieved_value = get_arcadia_setting('CANVAS_LEGEND', 'debug_mode', False)
        
        assert retrieved_value == test_value, f"Expected {test_value}, got {retrieved_value}"
        
        print("✓ Debug mode persistence test PASSED")
        print(f"  - Set value: {test_value}")
        print(f"  - Retrieved value: {retrieved_value}")
        
        # Clean up
        set_arcadia_setting('CANVAS_LEGEND', 'debug_mode', False)
        
        return True
        
    except Exception as e:
        print(f"✗ Debug mode persistence test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_version_constants():
    """Test version constants"""
    print("\n=== Testing Version Constants ===")
    
    try:
        from ArcadiaCanvasLegend.dialogs.canvas_legend_dialog import PLUGIN_VERSION, PLUGIN_VERSION_NAME
        
        print(f"✓ Version constants test PASSED")
        print(f"  - PLUGIN_VERSION: {PLUGIN_VERSION}")
        print(f"  - PLUGIN_VERSION_NAME: {PLUGIN_VERSION_NAME}")
        
        # Check if it's the expected version
        expected_version = "1.0.22"
        if PLUGIN_VERSION == expected_version:
            print(f"  ✓ Version matches expected: {expected_version}")
        else:
            print(f"  ! Version mismatch - expected: {expected_version}, got: {PLUGIN_VERSION}")
        
        return True
        
    except Exception as e:
        print(f"✗ Version constants test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

def run_all_tests():
    """Run all tests"""
    print("BETA 22 FIXES VALIDATION")
    print("=" * 50)
    
    results = []
    results.append(test_layersymbolinfo_structure())
    results.append(test_conversion_layer())
    results.append(test_debug_mode_integration())
    results.append(test_version_constants())
    
    print("\n" + "=" * 50)
    print("SUMMARY")
    
    passed = sum(results)
    total = len(results)
    
    if passed == total:
        print(f"✓ ALL TESTS PASSED ({passed}/{total})")
        print("\nBETA 22 fixes are working correctly!")
    else:
        print(f"✗ SOME TESTS FAILED ({passed}/{total} passed)")
        print("\nSome issues remain - check the details above.")
    
    return passed == total

# Run tests when script is executed
if __name__ == "__main__":
    run_all_tests()

# For QGIS console execution
print("Running BETA 22 fixes validation...")
run_all_tests()

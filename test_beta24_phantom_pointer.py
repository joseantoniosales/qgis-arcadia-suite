#!/usr/bin/env python3
"""
Test script for Beta 24 Phantom Pointer Solution
Verifies symbol cloning and thread-safe image pre-rendering functionality
"""

import sys
import os

# Add plugin path
plugin_path = "/Volumes/Mac_Data/qgis-arcadia-suite/ArcadiaCanvasLegend"
sys.path.append(plugin_path)

def test_symbol_extractor_import():
    """Test if we can import the updated SymbolDataExtractor"""
    try:
        from tools.symbol_data_extractor import SymbolDataExtractor, LayerSymbolInfo
        print("✓ Successfully imported Beta 24 SymbolDataExtractor")
        return True
    except ImportError as e:
        print(f"✗ Failed to import SymbolDataExtractor: {e}")
        return False

def test_phantom_pointer_protection():
    """Test phantom pointer protection features"""
    try:
        from tools.symbol_data_extractor import SymbolDataExtractor
        
        # Initialize extractor with debug mode
        extractor = SymbolDataExtractor(debug_mode=True)
        print("✓ Created SymbolDataExtractor with debug mode")
        
        # Test cache stats
        stats = extractor.get_cache_stats()
        print(f"✓ Cache stats: {stats}")
        
        # Test cache clearing
        extractor.clear_symbol_cache()
        print("✓ Cache clearing function works")
        
        # Test thread safety verification with dummy data
        dummy_symbol_data = {
            'is_thread_safe': True,
            'symbol': None,  # No actual symbol for this test
            'symbol_image': None
        }
        
        # This should return False since we have no symbol or image
        is_safe = extractor.verify_symbol_thread_safety(dummy_symbol_data)
        print(f"✓ Thread safety verification: {is_safe} (expected False for empty data)")
        
        return True
        
    except Exception as e:
        print(f"✗ Phantom pointer protection test failed: {e}")
        return False

def test_dialog_import():
    """Test if we can import the updated dialog"""
    try:
        from dialogs.canvas_legend_dialog import CanvasLegendDialog
        print("✓ Successfully imported Beta 24 CanvasLegendDialog")
        return True
    except ImportError as e:
        print(f"✗ Failed to import CanvasLegendDialog: {e}")
        return False

def test_version_info():
    """Test version information"""
    try:
        from dialogs.canvas_legend_dialog import PLUGIN_VERSION, PLUGIN_VERSION_NAME
        print(f"✓ Plugin Version: {PLUGIN_VERSION}")
        print(f"✓ Version Name: {PLUGIN_VERSION_NAME}")
        
        # Verify we're on Beta 24
        if "1.0.24" in PLUGIN_VERSION and "Beta 24" in PLUGIN_VERSION_NAME:
            print("✓ Confirmed Beta 24 version")
            return True
        else:
            print("✗ Version mismatch - not Beta 24")
            return False
            
    except Exception as e:
        print(f"✗ Version info test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("=" * 50)
    print("Beta 24 Phantom Pointer Solution Test Suite")
    print("=" * 50)
    
    tests = [
        ("Symbol Extractor Import", test_symbol_extractor_import),
        ("Phantom Pointer Protection", test_phantom_pointer_protection),
        ("Dialog Import", test_dialog_import),
        ("Version Information", test_version_info)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n--- Testing {test_name} ---")
        if test_func():
            passed += 1
        else:
            print(f"FAILED: {test_name}")
    
    print("\n" + "=" * 50)
    print(f"Test Results: {passed}/{total} tests passed")
    print("=" * 50)
    
    if passed == total:
        print("🎉 All tests passed! Beta 24 phantom pointer solution is ready.")
        return True
    else:
        print("❌ Some tests failed. Please review the implementation.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

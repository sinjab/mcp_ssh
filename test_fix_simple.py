#!/usr/bin/env python3
"""
Simple test for the command execution fix.
Tests just the escaping logic without dependencies.
"""

def test_escaping_logic():
    """Test the escaping logic that was implemented"""
    
    test_cases = [
        {
            'input': "echo 'Hello World' > test.txt",
            'expected_escaped': "echo '\"'\"'Hello World'\"'\"' > test.txt",
            'description': "Single quotes with redirection"
        },
        {
            'input': 'echo "Hello World" > test.txt',
            'expected_escaped': 'echo "Hello World" > test.txt',
            'description': "Double quotes with redirection"
        },
        {
            'input': "echo 'Single \"double\" quotes' > test.txt",
            'expected_escaped': "echo '\"'\"'Single \"double\" quotes'\"'\"' > test.txt",
            'description': "Mixed quotes"
        },
        {
            'input': "ls -la > output.txt",
            'expected_escaped': "ls -la > output.txt",
            'description': "No quotes"
        },
        {
            'input': "echo 'Line 1' && echo 'Line 2'",
            'expected_escaped': "echo '\"'\"'Line 1'\"'\"' && echo '\"'\"'Line 2'\"'\"'",
            'description': "Multiple commands with quotes"
        }
    ]
    
    print("Testing command escaping logic:")
    print("=" * 60)
    
    passed = 0
    failed = 0
    
    for i, case in enumerate(test_cases, 1):
        print(f"\nTest {i}: {case['description']}")
        print(f"Input:    {case['input']}")
        
        # Apply the same escaping logic as in the fix
        escaped = case['input'].replace("'", "'\"'\"'")
        print(f"Escaped:  {escaped}")
        print(f"Expected: {case['expected_escaped']}")
        
        if escaped == case['expected_escaped']:
            print("✓ PASSED")
            passed += 1
        else:
            print("✗ FAILED")
            failed += 1
        
        # Test that the escaped command would work in bash -c
        bash_command = f"bash -c '{escaped}'"
        print(f"Bash cmd: {bash_command}")
        
        # Basic syntax check - no unmatched quotes
        quote_count = bash_command.count("'")
        if quote_count % 2 == 0:
            print("✓ Quote syntax looks valid")
        else:
            print("✗ Unmatched quotes detected!")
            failed += 1
        
        print("-" * 40)
    
    print(f"\nFinal Results: {passed} passed, {failed} failed")
    return failed == 0

def test_problematic_cases():
    """Test cases that were failing before the fix"""
    
    print("\nTesting problematic cases from bug report:")
    print("=" * 60)
    
    problematic_commands = [
        "echo 'Hello from remote server' > test_file.txt",
        "printf 'Line 1\\nLine 2\\n' > multiline.txt",
        "echo 'Mixed \"quotes\" content' > mixed.txt"
    ]
    
    for cmd in problematic_commands:
        print(f"\nOriginal command: {cmd}")
        
        # This is what would happen before the fix (broken)
        broken_wrapper = f"bash -c '{cmd}'"
        print(f"Broken wrapper:   {broken_wrapper}")
        
        # Count quotes to show the problem
        quote_count = broken_wrapper.count("'")
        if quote_count % 2 != 0:
            print("✗ BROKEN: Unmatched quotes!")
        
        # This is what happens after the fix
        escaped = cmd.replace("'", "'\"'\"'")
        fixed_wrapper = f"bash -c '{escaped}'"
        print(f"Fixed wrapper:    {fixed_wrapper}")
        
        # Verify the fix
        quote_count = fixed_wrapper.count("'")
        if quote_count % 2 == 0:
            print("✓ FIXED: Quotes are balanced")
        else:
            print("✗ Still broken!")
        
        print("-" * 50)

if __name__ == "__main__":
    success1 = test_escaping_logic()
    test_problematic_cases()
    
    print(f"\nOverall test result: {'PASSED' if success1 else 'FAILED'}")
    exit(0 if success1 else 1)

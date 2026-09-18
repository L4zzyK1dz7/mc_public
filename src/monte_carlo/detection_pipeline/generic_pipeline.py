"""
Generic detection pipeline for platforms with generic sensors.

1. Check sensor interval time
2. Check Target in FOV
3. Get PoD value based on distance to the target
4. Evaluate PoD against Rnd number and record result into sliding window
5. Evaluate K-of-n
"""

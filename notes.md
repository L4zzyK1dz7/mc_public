05/08/2026
Draft Platform doesnt do anything now, just use dataclasses 

21/08/2026
Use a shared model for config models 

30/08/2026 (16:49)
Fixed the pydantic validation error, needed to redefine the platforms by dumping it into a new dict (might need to do it for sensors but i think it handles that autonmatically )
Need to fix the sensor manual and import tab. Does not allow k-of-n options 

09/09/2026
Factory pattern: theres the if else statements and theres the faster hashmap lookup and better O/C as you don't need to update the method only insert the class and the hashmap

Strategy pattern is used to define the "HOW" of an existing object. Factory patterns creates the sensors so sensor 1 and sensor 2 is created using the factory pattern, the strategy pattern defines which weapon to use e.g. generic or special. 

States should be considered for future work. Other future work is Multi static active sonar 


12/09/2026
Completed sensor validation, created factory pattern with human readable error message handling. Allowed k-of-n options in streamlit. 
Completed Movement Type Strategy Pattern. 

Next steps:
- Prevent Platform and sensor creation with same name in the UI  - Done 23/09/2026
- Barrier movement and waypoint movement 
- test Team base detection.
- Sensor Config now only takes Generic and Specific changed PlatformConfig to accept them two instead of the base allowing .csv to retain the config data instead of just the baseclass. 23/09/2026
- Start Monte Carlo Engine and Create summary stats and raw_positions.csv  - 23/09/26 done 
- Connect the outputs with plotly UI visuals - 23/09/26 done 

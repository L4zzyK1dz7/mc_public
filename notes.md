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
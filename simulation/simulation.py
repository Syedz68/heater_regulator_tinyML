
# Some physical constants, used for filling out the formulas for the physics emulation
class PhysicalConstants:
    fiberglassInsulationThermalConductivityCoefficient = 0.035 # (w/m*C) / (w/m*K) Source : https://sandwichpaneltlbd.com/thermal-conductivity-understanding-fiberglass-insulation/
    airDensity = 1.1839 # (Kg) Source: https://en.wikipedia.org/wiki/Density_of_air
    airHeatCapacityIsobaric = 1006  # (J/Kg*m) Source: https://en.wikipedia.org/wiki/Table_of_specific_heat_capacities

# A heater has a maximum effect at which it can operate. The output is a float between 0 and 1,
# representing how much of its max effect the heater should output. The heater is off by default. 
class Heater:
    def __init__(self,maxEffect):
        self.maxEffect = maxEffect # (W)
        self.output = 0 # should be a float between 0 and 1, gets multiplied with effect
        self.nrOfSwitches = 0
    def __str__(self):
        return f"Heater with effect of {self.maxEffect} is outputting at {self.output} max capacity."
    def setOutput(self,output):
        if(((self.output==1) and (output == 0)) or ((self.output==0) and (output>0))):
            self.nrOfSwitches+=1
        self.output = output
        
    def getEffectiveOutput(self):
        return self.maxEffect * self.output

# A rectangular room with walls of variable thickness and materials.
class Room:
    def __init__(self,width,length,height,wallThickness,wallThermalConductivityCoefficient):
        self.width = width      # (m)
        self.length = length    # (m)
        self.height = height    # (m)
        self.wallThickness = wallThickness # (m)
        self.wallThermalConductivityCoefficient = wallThermalConductivityCoefficient # (w/Kg*C)
    def __str__(self):
        return f"Room attributes: width={self.width}, length={self.length}, height={self.height}, wallThickness={self.wallThickness}, wallThermalConductivityCoefficient={self.wallThermalConductivityCoefficient}"   

class Ventilation:
    def __init__(self,airChangeRatePerHour,volumeInQuadraticMeters):
        self.airChangeRatePerHour = airChangeRatePerHour
        self.volumeInQuadraticMeters = volumeInQuadraticMeters
        self.isOn = True
    def calculateSuppliedAirInKg(self,timestepInSeconds):
        if(self.isOn): return (((self.airChangeRatePerHour * self.volumeInQuadraticMeters) / 3600) * timestepInSeconds * PhysicalConstants.airDensity)
        else: return 0

# A physics simulation of a room with an inside and outside temperature. Time passes by
# the tick() method.
class SimEnv:    
    def __init__(self, room, heater, ventilation, insideTemperatureInCelsius, outsideTemperatureInCelsius):
        self.room = room
        self.heater = heater
        self.insideTemperatureInCelsius = insideTemperatureInCelsius
        self.outsideTemperatureInCelsius = outsideTemperatureInCelsius
        self.time = 0 # (s)
        self.totalPowerUsage = 0 # (J)
        self.ventilation = ventilation

    # Update physics simulation with specified timestep.
    def tick(self,timeStepInSeconds):
        self.time+=timeStepInSeconds
        totalSurfaceArea = self.room.length * self.room.height * 2 + self.room.width * self.room.height * 2 + self.room.width * self.room.length * 2;
        heatTransferThroughWallsRate = calculateHeatDissipationRateInWatt(
            self.room.wallThermalConductivityCoefficient,
            totalSurfaceArea,
            self.insideTemperatureInCelsius-self.outsideTemperatureInCelsius,
            self.room.wallThickness
        )
        
        sumHeatTransferRate = self.heater.getEffectiveOutput() - heatTransferThroughWallsRate
        deltaEnergyWithinTimeframe = sumHeatTransferRate * timeStepInSeconds
        self.totalPowerUsage += self.heater.getEffectiveOutput() * timeStepInSeconds
        massOfAirInRoom = self.room.width * self.room.length * self.room.height * PhysicalConstants.airDensity
        deltaEnergyWithinTimeframe += calculateHeatTransferInJoules(PhysicalConstants.airHeatCapacityIsobaric,
                                                                    self.ventilation.calculateSuppliedAirInKg(timeStepInSeconds),
                                                                    (self.outsideTemperatureInCelsius-self.insideTemperatureInCelsius))
        temperatureChangeInCelsius = calculateTemperatureChangeInCelsius(deltaEnergyWithinTimeframe,
                                                                         PhysicalConstants.airHeatCapacityIsobaric, 
                                                                         massOfAirInRoom)
        self.insideTemperatureInCelsius += temperatureChangeInCelsius
    def __str__(self):
        return f"Inside temperature at time {self.time} s is {self.insideTemperatureInCelsius} degrees Celsius. Total power use = {self.totalPowerUsage} Joules."

# Returns rate at which thermal energy dissipates (W)
# Uses Q = kAT/x formula Source : https://www.youtube.com/watch?v=AOkCH2G2vX0
# Note that Q has unit W here and unit J in the other heat transfer formula.
def calculateHeatDissipationRateInWatt(k ,A, DT,x):    
    return (k * A * DT) / x
# Returns change in temperature when Q(J) energy is introduced to 
# a mass with heat capacity c (J/Kg/Celsius) and mass m(Kg).
# Uses heat transfer formula ( Q=c*m*DT ) : https://www.geeksforgeeks.org/physics/heat-transfer-formulas/
def calculateTemperatureChangeInCelsius(Q,c,m):
    return Q/(c*m)
# Just regular heat transfer formula (Q=c*m*DT)
def calculateHeatTransferInJoules(c,m,DT):
    return c*m*DT

#------------ Example usage ---------------# Remove comments and run to test
#import time
#roomLength = 5      # (m)
#roomWidth = 5       # (m)
#roomHeight = 3      # (m)
#wallThickness = 0.2 # (m)
#heaterEffect = 2000 # (W) Based on https://www.jula.se/catalog/bygg-och-farg/varme-och-ventilation/uppvarmning/elektriska-element/konvektorelement-025189/
#airChangeRatePerHour = 0.5 # Based on minimum in living spaces: https://www.ventomaxx.de/en/blog/understanding-minimum-air-change-rate/

#room = Room(roomLength,roomWidth,roomHeight,wallThickness,PhysicalConstants.fiberglassInsulationThermalConductivityCoefficient)
#heater = Heater(heaterEffect)
#vent = Ventilation(airChangeRatePerHour,room.height+room.width+room.length)
#vent.isOn=True
#simulation = SimEnv(room,heater,vent,20,0)
#heater.setOutput=1
#x = 10000000
#while(x>0):
#    simulation.tick(1) # 1 second timesteps
#    
#    if(simulation.time%(90) == 0): # print every 15 min
#        print(simulation)
#        time.sleep(0.5)
#    x-=1
#    if(simulation.insideTemperatureInCelsius > 24):
#        heater.output = 0
#    if(simulation.insideTemperatureInCelsius < 20):
#        heater.output = 1
#-----------------------------------------#
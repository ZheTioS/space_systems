import comtypes.client

def main():
    # Define the names of the existing scenario and satellite
    scenarioName = 'small_sat_const_study'
    satelliteName = '3U_cubesat'

    # Initialize and connect to STK
    try:
        # Grab an existing instance of STK
        uiapp = comtypes.client.GetActiveObject('STK11.Application')
        root = uiapp.Personality2
        uiapp.Visible = True
        
        # Check if the desired scenario is loaded
        try:
            scenario = root.GetObjectFromPath(f'/Scenario/{scenarioName}')
            print(f'Connected to existing scenario: {scenarioName}')
        except comtypes.COMError:
            raise RuntimeError(f'Scenario "{scenarioName}" not found. Please load the scenario in STK.')
    except (OSError, comtypes.COMError):
        raise RuntimeError('STK is not running. Please start STK and load the desired scenario.')

    # Retrieve the epoch from the scenario
    epoch = scenario.StartTime
    print(f'Scenario Epoch: {epoch}')

    # Check if the desired satellite exists
    try:
        satellite = root.GetObjectFromPath(f'/Scenario/{scenarioName}/Satellite/{satelliteName}')
        print(f'Found existing satellite: {satelliteName}')
    except comtypes.COMError:
        raise RuntimeError(f'Satellite "{satelliteName}" not found in scenario "{scenarioName}".')

    # Retrieve all facilities
    facilities = scenario.Children.GetElements('eFacility')
    numFacilities = facilities.Count
    print(f'Number of facilities: {numFacilities}')

    # Loop through each facility
    for i in range(numFacilities):
        facility = facilities.Item(i)
        facilityName = facility.InstanceName
        print(f'Processing facility: {facilityName}')
        
        # Create a new coverage definition for each facility
        covDef = scenario.Children.New('eCoverageDefinition', f'CovDef_{facilityName}')
        covDef.AssetList.Add(satellite.Path)
        covDef.PointDefinition.IndividualPoints.Add('Facility', facility.Path)
        covDef.ComputeAccesses()
        
        # Add a Figure of Merit for Revisit Time
        fom = covDef.Children.New('eFigureOfMerit', f'Fom_{facilityName}')
        fom.SetDefinitionType('eFmRevisitTime')
        fom.Definition.Satisfaction.EnableSatisfaction = True
        
        # Find min/max FOM value for static contours
        overallValDP = fom.DataProviders.GetDataPrvFixedFromPath('Overall Value')
        Result_1 = overallValDP.Exec()
        minVal = Result_1.DataSets.GetDataSetByName('Minimum').GetValues()
        maxVal = Result_1.DataSets.GetDataSetByName('Maximum').GetValues()
        
        # Configure contours
        contours = fom.Graphics.Static.Contours
        contours.IsVisible = True
        contours.ContourType = 'eSmoothFill'
        contours.ColorMethod = 'eColorRamp'
        contours.LevelAttributes.RemoveAll()
        contours.LevelAttributes.AddLevelRange(minVal, maxVal, (maxVal - minVal) / 10)
        contours.RampColor.StartColor = 255        # Red
        contours.RampColor.EndColor = 16711680     # Blue
        
        # Pull the Percent Satisfied as a value
        staticSatDP = fom.DataProviders.GetDataPrvFixedFromPath('Static Satisfaction')
        Result_2 = staticSatDP.Exec()
        Percent_1 = Result_2.DataSets.GetDataSetByName('Percent Satisfied').GetValues()
        
        # Display results
        print(f'Facility: {facilityName}, Percent Satisfied: {Percent_1:.2f}%')

    # Create a new coverage definition
    covDef = scenario.Children.New('eCoverageDefinition', 'CovDef')
    covDef.AssetList.Add(satellite.Path)
    covDef.ComputeAccesses()

    # Add a Figure of Merit for Revisit Time
    fom = covDef.Children.New('eFigureOfMerit', 'Fom')
    fom.SetDefinitionType('eFmRevisitTime')
    fom.Definition.Satisfaction.EnableSatisfaction = True

    # Find min/max FOM value for static contours
    overallValDP = fom.DataProviders.GetDataPrvFixedFromPath('Overall Value')
    Result_1 = overallValDP.Exec()
    minVal = Result_1.DataSets.GetDataSetByName('Minimum').GetValues()
    maxVal = Result_1.DataSets.GetDataSetByName('Maximum').GetValues()

    # Configure contours
    contours = fom.Graphics.Static.Contours
    contours.IsVisible = True
    contours.ContourType = 'eSmoothFill'
    contours.ColorMethod = 'eColorRamp'
    contours.LevelAttributes.RemoveAll()
    contours.LevelAttributes.AddLevelRange(minVal, maxVal, (maxVal - minVal) / 10)
    contours.RampColor.StartColor = 255        # Red
    contours.RampColor.EndColor = 16711680     # Blue

    # Pull the Percent Satisfied as a value
    staticSatDP = fom.DataProviders.GetDataPrvFixedFromPath('Static Satisfaction')
    Result_2 = staticSatDP.Exec()
    Percent_1 = Result_2.DataSets.GetDataSetByName('Percent Satisfied').GetValues()

    # Get Grid Inspector Tool Data
    gridInspector = fom.GridInspector
    Lat = 42.1429
    Lon = 4.00000
    gridInspector.SelectPoint(Lat, Lon)

    # Output the same message as in the Grid Inspector
    print(gridInspector.Message)

    # Compute Access Here
    pointFOM = gridInspector.PointFOM
    pointFOMResult = pointFOM.Exec('30 Jun 2015 04:00:00.000', '31 Jun 2015 04:00:00.000', 60)
    print(pointFOMResult.DataSets.Count)
    answer = pointFOMResult.DataSets.GetRow(0)
    ans_Interval = answer[0]
    ans_Duration = answer[1]

    # Display results
    print(f'Interval Start: {ans_Interval}')
    print(f'Revisit Duration: {ans_Duration:.2f} seconds')

if __name__ == "__main__":
    main()
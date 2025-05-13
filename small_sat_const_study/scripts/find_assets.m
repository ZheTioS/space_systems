uiapp = actxGetRunningServer('STK11.Application');
root = uiapp.Personality2;
scen = root.CurrentScenario;

% Use the exact object path for the satellite
satellitePath = '/Scenario/small_sat_const_study/Satellite/3U_cubesat';

try
    sat = root.GetObjectFromPath(satellitePath);
    disp(['? Found satellite: ', char(sat.InstanceName)]);
catch ME
    disp(['? Could not find satellite at path: ', satellitePath]);
    disp(ME.message);
end

try
    % Try to connect to existing STK instance
    uiapp = actxGetRunningServer('STK11.Application');
catch
    % Fallback: create a new instance if none is running
    uiapp = actxserver('STK11.Application');
end

uiapp.Visible = 1;
root = uiapp.Personality2;

% Now test if a scenario is open
if isempty(root.CurrentScenario)
    disp('Connected to STK, but no scenario is loaded.');
else
    disp(['Connected to scenario: ', root.CurrentScenario.InstanceName]);
end

if isempty(root.CurrentScenario)
    disp('? No scenario is active in STK.');
else
    disp(['? Scenario open: ', root.CurrentScenario.InstanceName]);
end
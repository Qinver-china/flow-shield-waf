-- Observe mode: no interception. Access layer records the event and lets the
-- request continue. This module exists for symmetry with the other actions.
local _M = {}

function _M.run(_ctx)
    return true  -- always "continue"
end

return _M

def create_groundstation_schedule(groundstation_metadata):
   """
   Uses necessary info from metadata to create a groundstation schedule.

   Args:
      groundstation_metadata: the metadata we recieve from the groundstation

   Returns: a schedule for a groundstation
   """

   # Instantiate a schedule object

   # Loop through the ground_station data and fill in/add to the schedule object

def relay_groundstation_sched(self, groundstation, metadata):
   """
   Event: on recieve of our own ground station metadata

   Extracts necessary info from metadata to create a groundstation schedule.
   Relays a groundstations schedule to a server (policy and mission).

   Args:
      self: maybe a policy server is an obejct with a list/set/dict of all servers
         (mission and policy) it is connected to. We will need addresses of both
         for communication.

      groundstation: some identifier for the ground station

      metadata: the metadata we recieve from the groundstation

   Returns:
   """
   groundstation_schedule = create_groundstation_schedule(metadata)

   # Relay the groundstation schedule to all connected servers
   # loop through all connected policy servers (SELF.POLICY_SERVERS)
      # forward groundstation schedule
   # loop throuhg all connecte mission servers (SELF.MISSION_SERVERS)
      # forward groundstation schedule

def fwd_groundstation_sched(self, policy_server, groundstation, schedule):
   """
   Event: On receive of another school's ground stations schedule from another
      school's server (policy)

   Forwards this schedule to its own servers (mission)

   Args:
      self: maybe a policy server is an obejct with a list/set/dict of all servers
         (mission and policy) it is connected to. We will need addresses of just
         the server (mission) for communication.

      policy_server: identifier for server (policy) that is in charge of the
         groundstation

      groundstation: some identifier for the ground station we are getting
         the schedule from

      schedule: a list of times and location a ground station is free

   Returns:
   """

   # For each connected mission server (SELF)
      # Forward your recieved schedule from someone else's groundstation (GROUNDSTATION)

def fwd_groundsation_request(self, mission_server, policy_server, groundstation, request_schedule):
   """
   Event: On receive of a schedule request for another school's ground station
      from our own server (mission)

   Forwards this schedule to other servers (policy)

   Args:
      self: maybe a policy server is an obejct with a list of all servers
      (mission and policy) it is connected to. We will need addresses of just
      the servers (policy) for communication.

      mission_server: the server (mission) that is reqeusting groundstation time

      policy_server: identifier for server (policy) that is in charge of the
         groundstation

      groundstation: the groundstation we want to request schedule time with.

      request_schedule: A schedule that a server (misison) wants from a
         groundstation

   Returns:
   """

   # tell Purdue's (or some school) policy server that I want this schedule

def sched_groundstation_request(self, mission_server, policy_server, groundstation, request_schedule):
   """
   Event: on recieve of requests for a server's (policy) our own groundstations

   Uses the comparator(or something) that the policy server uses to determine
   how much time the requesting server (mission) gets with the groundstation
   schedules that time into its own table, and relays the decision back to the
   policy server for which the requesting misison server is under.

   Args:
      requester: the server making the request. since we have a list of all servers we
         are connected to, we can probbaly just have a requester be an ID for which
         we can LU into our local list of servers and get the requester address so we
         can send the confirmation/deny of their groundstation request

      mission_server: the server (mission) that is making the request for ground
         station time

      policy_server: identifier for server (policy) that is in charge of the
         groundstation

      groundstation: the groundstation requested

   Returns: Nothing
   """

def control_groundstation(self):
   """
   Event: On recieve time notification from our groundstation_schedules

   Tells the groundstation to connect to the mission server for the time specified
   by our schedule

   Args:
      self:
         groundstation_schedule: the schedule

         groundstation: the groundstation related to the schedule. The ground
            station will initiate the request with the mission_Server specified

         mission_server_address: the mission server the the requested time, will
            will now get its time

   Returns: Nothing
   """
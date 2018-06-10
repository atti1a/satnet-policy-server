from policy_server import PS
import sched, time

def test_ms_init():
   pass

def print_response(function_name, response):
   print "calling " + function_name + "()----------------------------------------------------------"
   for dest, packet in response.items():
      print dest
      print packet
   print "--------------------------------------------------------"

def test_handle_request():
   policy_server = PS(sched.scheduler(time.time, time.sleep))

   #region TEST - One groundstation with all of them conflicting
   #************************************************************************************************
   #one_gs_with_conflicts = [
   #   {"reqID": "12-0", "gsID": 0, "start": 0, "end":1, "wd": False},
   #   {"reqID": "12-1", "gsID": 0, "start": 0, "end":1, "wd": False},
   #   {"reqID": "12-2", "gsID": 0, "start": 0, "end":1, "wd": False},
   #   {"reqID": "12-3", "gsID": 0, "start": 0, "end":1, "wd": False},
   #   {"reqID": "12-4", "gsID": 0, "start": 0, "end":1, "wd": False},
   #   {"reqID": "12-5", "gsID": 0, "start": 0, "end":1, "wd": False},
   #]
   #policy_server.gs_set.remove(0)
   #################################################################################################
   #endregion

   #region TEST - Two groundstations with no conflicts
   #************************************************************************************************
   #gs_metadata = [
   #   {"gsID": 3, "lat": 1, "long": 1},
   #   {"gsID": 4, "lat": 8, "long": 3}
   #]
   #two_gs_with_no_conflict = [
   #   {"reqID": "12-0", "gsID": 1, "start": 0, "end":1, "wd": False},
   #   {"reqID": "12-1", "gsID": 1, "start": 2, "end":3, "wd": False},
   #   {"reqID": "12-2", "gsID": 1, "start": 4, "end":5, "wd": False},
   #   {"reqID": "12-3", "gsID": 2, "start": 1, "end":5, "wd": False},
   #   {"reqID": "12-4", "gsID": 3, "start": 6, "end":8, "wd": False},
   #   {"reqID": "12-5", "gsID": 2, "start": 20, "end":234, "wd": False},
   #]

   #policy_server.add_groundstation(1, 1, 8)
   #policy_server.add_groundstation(2, 3, 9)
   #response = policy_server.fwd_stripped_gs_metadata(gs_metadata, "conn1")
   #print_response('fwd_stripped_gs_metadata', response)
   #response = policy_server.handle_requests(two_gs_with_no_conflict, "abc")
   #print_response('handle_requests', response)
   #################################################################################################
   #endregion

   #region TEST - two groundstations with some conflicts
   #************************************************************************************************
   gs_metadata = [
      {"gsID": 3, "lat": 1, "long": 1},
      {"gsID": 4, "lat": 8, "long": 3}
   ]
   ms1_two_gs_with_no_conflicts = [
      {"reqID": "1-0", "gsID": 1, "start": 0, "end": 1, "wd": False},
      {"reqID": "1-2", "gsID": 1, "start": 4, "end": 5, "wd": False},
      {"reqID": "1-3", "gsID": 2, "start": 1, "end": 5, "wd": False},
      {"reqID": "1-4", "gsID": 3, "start": 6, "end": 8, "wd": False},
      {"reqID": "1-5", "gsID": 2, "start": 20, "end": 234, "wd": False},
   ]
   ms2_two_gs_with_one_conflict = [
      {"reqID": "2-1", "gsID": 1, "start": 2, "end": 3, "wd": False},
      {"reqID": "2-2", "gsID": 1, "start": 4, "end": 5, "wd": False},
      {"reqID": "2-3", "gsID": 2, "start": 6, "end": 7, "wd": False},
      {"reqID": "2-4", "gsID": 3, "start": 1, "end": 2, "wd": False},
      {"reqID": "2-5", "gsID": 2, "start": 9, "end": 11, "wd": False},
   ]
   ms3_two_gs_with_two_conflicts = [
      {"reqID": "3-1", "gsID": 1, "start": 2, "end": 3, "wd": False},
      {"reqID": "3-2", "gsID": 1, "start": 4, "end": 5, "wd": False},
      {"reqID": "3-3", "gsID": 2, "start": 21, "end": 40, "wd": False},
   ]
   ms2_two_gs_with_one_conflict = [
      {"reqID": "1-3", 'gsID': 1, "wd": True}
   ]

   policy_server.add_groundstation(1, 1, 8)
   policy_server.add_groundstation(2, 3, 9)
   response = policy_server.fwd_stripped_gs_metadata(gs_metadata, "purdue")
   print_response('fwd_stripped_gs_metadata', response)
   response = policy_server.handle_requests(ms1_two_gs_with_no_conflicts, "ms1")
   print_response('handle_requests', response)
   response = policy_server.handle_requests(ms2_two_gs_with_one_conflict, "ms2")
   print_response('handle_requests', response)
   response = policy_server.handle_requests(ms3_two_gs_with_two_conflicts, "ms3")
   print_response('handle_requests', response)
   #################################################################################################
   #endregion

def main():
   test_handle_request()

if __name__ == '__main__':
    main()
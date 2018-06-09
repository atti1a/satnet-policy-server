from policy_server import PS
import sched, time

def test_ms_init():
   pass

def test_handle_request():
   policy_server = PS(sched.scheduler(time.time, time.sleep))

   # TEST - One groundstation with all of them conflicting
   policy_server.gs_set.add(0)
   one_gs_with_conflicts = [
      {"reqID": "12-0", "gsID": 0, "start": 0, "end":1, "wd": False},
      {"reqID": "12-1", "gsID": 0, "start": 0, "end":1, "wd": False},
      {"reqID": "12-2", "gsID": 0, "start": 0, "end":1, "wd": False},
      {"reqID": "12-3", "gsID": 0, "start": 0, "end":1, "wd": False},
      {"reqID": "12-4", "gsID": 0, "start": 0, "end":1, "wd": False},
      {"reqID": "12-5", "gsID": 0, "start": 0, "end":1, "wd": False},
   ]
   policy_server.gs_set.remove(0)

   # TEST - Two groundstations with no conflicts
   policy_server.gs_set.add(1)
   policy_server.gs_set.add(2)
   policy_server.foreign_gs[1] = 'conn1'
   policy_server.foreign_gs[2] = 'conn2'
   two_gs_with_no_conflict = [
      {"reqID": "12-0", "gsID": 1, "start": 0, "end":1, "wd": False},
      {"reqID": "12-1", "gsID": 1, "start": 2, "end":3, "wd": False},
      {"reqID": "12-2", "gsID": 1, "start": 4, "end":5, "wd": False},
      {"reqID": "12-3", "gsID": 2, "start": 1, "end":5, "wd": False},
      {"reqID": "12-4", "gsID": 3, "start": 6, "end":8, "wd": False},
      {"reqID": "12-5", "gsID": 2, "start": 20, "end":234, "wd": False},
   ]
   response = policy_server.handle_requests(two_gs_with_no_conflict, "abc")
   for dest, packet in response.items():
      print dest
      print packet
   policy_server.gs_set.remove(1)
   policy_server.gs_set.remove(2)

   #TEST - two groundstations with some conflicts

def main():
   test_handle_request()

if __name__ == '__main__':
    main()
#!/usr/bin/env python

# Copyright (C) 2013 National Cheng Kung University, Taiwan
# All rights reserved.

# Configure wether to trace these feature
# Warning : Too many contents may freeze Grasp
import sys, getopt

TRACE_QUEUE = True
TRACE_MUTEX = True
TRACE_BINARY_SEMAPHORE = False
TRACE_INTERRUPT = False

cxt_sw_title = "vTaskSwitchContext"

def usage():
	print 'Usage: log2grasp.py [-f|-h]'
	print '-f, --full-context'
	print '\tful cost for context switch'
	print '-h, --help'
	print '\tprint this help meun'

def main(argv):
	global cxt_sw_title

	try:
		opts, args = getopt.getopt(argv,"hf",["--full-context", "--help"])
	except getopt.GetoptError:
		usage();
		sys.exit(2)
	for opt, arg in opts:
		if opt in ("h", "--help"):
			usage()
			sys.exit(0)
		elif opt in ("-f", "--full-context"):
			cxt_sw_title = "ContextSwitch"

if __name__ == "__main__":
	   main(sys.argv[1:])

log = open('log', 'r')
lines = log.readlines()

cxt_sw_cost = open('%s.log' % cxt_sw_title, 'w')

cxt_sw_cost.write('[%-20s]\t[%-20s]\t %s (microseconds)\n' %("Out Task", "In Task", "Cost"))
cxt_sw_cost.write('-------------------------------------------------------------------------\n')

tasks = {}
events = []
mutexes = {}
all_queues = {}
binsems = {}
queues = {}
total_cost = 0
cxt_sw_times = 0

for line in lines :
	line = line.strip()
	inst, args = line.split(' ', 1)
	
	if inst == 'task' :
		id, priority, name = args.split(' ', 2)
		
		task = {}
		task['no'] = str(len(tasks) + 1)
		task['priority'] = int(priority)
		task['name'] = task['no'] + ": " + name.strip()
		task['created'] = True
		
		tasks[id] = task
		
	elif inst == 'switch' :
		out_task, in_task, tick, tick_reload, out_minitick, in_minitick = args.split(' ')
		
		out_time = (int(tick) + (int(tick_reload) - int(out_minitick)) / float(tick_reload)) / 100 * 1000;
		in_time  = (int(tick) + (int(tick_reload) - int(in_minitick))  / float(tick_reload)) / 100 * 1000;

		cost = ((in_time - out_time) * 1000)
		total_cost += cost
		cxt_sw_times += 1
		
		event = {}
		event['type'] = 'task out'
		event['task'] = out_task
		event['time'] = out_time
		event['next'] = in_task
		# microsecond for the cost of the context switch
		event['cs_cost'] = cost
		events.append(event);

		event = {}
		event['type'] = 'task in'
		event['task'] = in_task
		event['time'] = in_time
		events.append(event);

		in_task_info = tasks[out_task]
		out_task_info = tasks[in_task]

		# microsecond for the cost of the context switch
		cxt_sw_cost.write('[%-20s]\t[%-20s]\t %4d\n' %(out_task_info['name'], in_task_info['name'], cost))


		last_task = in_task

	elif inst == 'mutex' and TRACE_MUTEX :
		task, id = args.split(' ')
		mutex = {}
		mutex['type'] = 'mutex'
		mutex['name'] = 'Mutex ' + str(len(mutexes) + 1)
		time, mutex['id'] = args.split(' ')
		mutexes[id] = mutex;
		all_queues[id] = mutex;

	elif inst == 'queue' :
		act, args = args.split(' ', 1)
		if act == 'create' :
			time, id, queue_type, queue_size = args.split(' ')

			if queue_type == '0' and TRACE_QUEUE :
				queue = {}
				queue['type'] = 'queue'
				queue['name'] = 'Queue ' + str(len(queues) + 1)
				queue['size'] = queue_size
				queues[id] = queue
				all_queues[id] = queue

			if queue_type == '3' and TRACE_BINARY_SEMAPHORE :	# Binary semaphore, see FreeRTOS/queue.c
				binsem = {}
				binsem['type'] = 'binary semaphore'
				binsem['name'] = "Binary Semaphore " + str(len(binsems) + 1)
				binsems[id] = binsem;
				all_queues[id] = binsem;

		elif act == 'send' or act == 'recv' :
			time, task_id, id = args.split(' ')
			if id in all_queues and int(time) > 0 :
				queue = all_queues[id]

				event = {}
				event['target'] = id
				event['task'] = task_id
				event['time'] = float(time) / 1000

				if queue['type'] == 'mutex' :
					event['type'] = 'mutex ' + ('take' if act == 'recv' else 'give')
					queue['acquired'] = True if act == 'recv' else False
					if act == 'recv' :
						queue['last_acquire'] = last_task

				elif queue['type'] == 'binary semaphore' :
					event['type'] = 'semaphore ' + ('take' if act == 'recv' else 'give')

				elif queue['type'] == 'queue' :
					event['type'] = 'queue ' + act

				# No type match
				else :
					continue

				# For interrupt, which is not declared explicitly
				if task_id not in tasks :
					task = {}
					task['no'] = str(len(tasks) + 1)
					task['priority'] = -1
					task['name'] = task['no'] + ": Interrupt " + task_id

					tasks[task_id] = task

				events.append(event);
		
		elif act == 'block' :
			time, task_id, id = args.split(' ')
			if id in all_queues and all_queues[id]['type'] == 'binary semaphore':
				event = {}
				event['target'] = id
				event['time'] = float(time) / 1000
				event['type'] = 'semaphore block'
				event['task'] = task_id

				events.append(event);

	elif inst == 'interrupt' :
		argv = (args + ' ').split(' ')
		dir, time, int_num = argv[0:3]

		if TRACE_INTERRUPT :
			if int_num not in tasks :
				task = {}
				task['no'] = str(len(tasks) + 1)
				task['priority'] = -int(argv[3]) - 1
				task['name'] = task['no'] + ": Interrupt " + int_num
				tasks[int_num] = task

			event = {}
			event['time'] = float(time) / 1000
			event['task'] = int_num

			if dir == 'in' :
				event['type'] = 'interrupt in'
				event['prev'] = last_task
				tasks[int_num]['prev'] = last_task
				last_task = int_num

			else :
				event['type'] = 'interrupt out'
				event['prev'] = tasks[int_num]['prev']
				last_task = tasks[int_num]['prev']

			events.append(event)
			tasks[int_num]['created'] = True if dir == 'in' else False

log.close()

cxt_sw_cost.write('-------------------------------------------------------------------------\n')
cxt_sw_cost.write('Total times for context switch: %d cost:%d average: %f\n' % (cxt_sw_times, total_cost, total_cost/cxt_sw_times))

cxt_sw_cost.close()

grasp = open('sched.grasp', 'w')

grasp.write('newTask taskCxtSwitch -priority 0  -name "%s" -color orange1\n' % (cxt_sw_title))
grasp.write('newBuffer BufferCxtSwitch -name "%s(us)"\n' % (cxt_sw_title))
grasp.write('bufferplot 0 resize BufferCxtSwitch 1\n')

for id in tasks :
	task = tasks[id]
	grasp.write('newTask task%s -priority %s %s -name "%s"\n' % (id, task['priority'], '-kind isr' if int(id) < 256 else '', task['name']))

for id in mutexes :
	mutex = mutexes[id]
	grasp.write('newMutex mutex%s -name "%s"\n' % (id, mutex['name']))

for id in binsems :
	sem = binsems[id]
	grasp.write('newSemaphore semaphore%s -name "%s"\n' % (id, sem['name']))

for id in queues :
	queue = queues[id]
	grasp.write('newBuffer Buffer%s -name "%s"\n' % (id, queue['name']))

for id in queues :
	queue = queues[id]
	grasp.write('bufferplot 0 resize Buffer%s %s\n' % (id, queue['size']))

for id in tasks :
	task = tasks[id]
	if int(id) > 255 or not TRACE_INTERRUPT :
		grasp.write('plot 0 jobArrived job%s.1 task%s\n' % (id, id))

for event in events :
	if event['type'] == 'task out' :
		grasp.write('plot %f jobPreempted job%s.1 -target job%s.1\n' %
				    (event['time'], event['task'], event['next']))
		grasp.write('plot %f jobArrived jobCxtSwitch taskCxtSwitch\n' % (event['time']))
		grasp.write('plot %f jobResumed jobCxtSwitch\n' % (event['time']))
		grasp.write('bufferplot %f push BufferCxtSwitch "%d"\n' % (event['time'], event['cs_cost']))
	elif event['type'] == 'task in' :
		grasp.write('plot %f jobResumed job%s.1\n' %
					(event['time'], event['task']))
		grasp.write('plot %f jobCompleted jobCxtSwitch\n' % (event['time']))
		grasp.write('bufferplot %f pop BufferCxtSwitch\n' % (event['time']))

	elif event['type'] == 'mutex give' :
		grasp.write('plot %f jobReleasedMutex job%s.1 mutex%s\n' % (event['time'], event['task'], event['target']));

	elif event['type'] == 'mutex take' :
		grasp.write('plot %f jobAcquiredMutex job%s.1 mutex%s\n'% (event['time'], event['task'], event['target']));

	elif event['type'] == 'queue send' :
		grasp.write('bufferplot %f push Buffer%s "%s"\n'% (event['time'], event['target'], tasks[event['task']]['no']));

	elif event['type'] == 'queue recv' :
		grasp.write('bufferplot %f pop Buffer%s\n'% (event['time'], event['target']));

	elif event['type'] == 'semaphore give' :
		grasp.write('plot %f jobReleasedSemaphore job%s.1 semaphore%s\n' % (event['time'], event['task'], event['target']));

	elif event['type'] == 'semaphore take' :
		grasp.write('plot %f jobAcquiredSemaphore job%s.1 semaphore%s\n'% (event['time'], event['task'], event['target']));

	elif event['type'] == 'semaphore block' :
		grasp.write('plot %f jobSuspendedOnSemaphore job%s.1 semaphore%s\n'% (event['time'], event['task'], event['target']));

	elif event['type'] == 'interrupt in' :
		grasp.write('plot %f jobArrived job%s.1 task%s\n' % (event['time'], event['task'], event['task']))
		grasp.write('plot %f jobResumed job%s.1\n' % (event['time'], event['task']))
		grasp.write('plot %f jobPreempted job%s.1 -target job%s.1\n' %
				    (event['time'], event['prev'], event['task']))

	elif event['type'] == 'interrupt out' :
		grasp.write('plot %f jobCompleted job%s.1\n' % (event['time'], event['task']))
		grasp.write('plot %f jobResumed job%s.1\n' % (event['time'], event['prev']))
		
# Clean up unended operations

for id in mutexes :
	mutex = mutexes[id]
	if mutex['acquired'] :
		grasp.write('plot %f jobReleasedMutex job%s.1 mutex%s\n' %
					(events[-1]['time'], mutex['last_acquire'], id));

for id in tasks :
	task = tasks[id]
	if 'created' in task and task['created'] :
		grasp.write('plot %f jobCompleted job%s.1\n' %
					(events[-1]['time'], id))

grasp.close()

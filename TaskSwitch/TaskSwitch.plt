set terminal pngcairo size 1024,768 enhanced font 'Verdana,10'
set output "TaskSwitch.png"
set autoscale
set grid
set title 'vTaskSwitchContext versus Full Context Switch'
set xlabel "Context (Task) Switch"
set ylabel "Cost (microsecond)"
plot 'vTaskSwitchContext/vTaskSwitchContext.dat' w lp t 'vTaskSwitchContext', 'full-context-switch/ContextSwitch.dat' w lp t 'Full Context Switch'

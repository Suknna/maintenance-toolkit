#!/usr/bin/env python3
# -*- coding: UTF-8 -*-


from vsphere_get_content import VsphereContent as vspc
from datetime import datetime, timedelta
import pytz
from pyVmomi import vim


class VspherePerformance(vspc):

    def __init__(self, ipaddress, user, passwd, days=None, starttime=None, endtime=None):

        super(VspherePerformance, self).__init__(ipaddress, user, passwd)
        self.starttime = starttime
        self.endtime = endtime
        self.days = days
        self.obj_vc_count = self.get_vcenter_object()
        self.obj_perf_mg = self.obj_vc_count.perfManager
        self.vctime_now = self.service_instance.CurrentTime().replace(microsecond=0)
        self.g_time = self.vctime_now - timedelta(seconds=3600)

        self.cycle = {"day": "300", "week": "1800", "month": "7200", "year": "66400"}

    def time_zone(self, tm):
        """
        :param tm: 传入datetime格式的时间
        :return: 将传入时间转换成UTC的时间
        """
        self.utc = pytz.timezone("UTC")
        self.utc_time = tm.astimezone(tz=self.utc)
        return self.utc_time

    def get_perf_msg(self):

        counter_info_list = list()
        obj_vc_perf_count = self.obj_perf_mg.perfCounter
        for counter in obj_vc_perf_count:
            counter_info_dict = dict()
            full_name = counter.groupInfo.key + "." + \
                        counter.nameInfo.key + "." + counter.rollupType
            name_nuit = full_name + "." + "unit"
            counter_info_dict[full_name] = counter.key
            counter_info_dict[name_nuit] = counter.unitInfo.label
            counter_info_list.append(counter_info_dict)

        return counter_info_list

    def get_hist_performance_data(self, obj_perfm, cycle=None, stime=None, etime=None):
        """
        :param obj_perfm: 需要获取性能的对象，例如:集群，物理机，虚拟机
        :param cycle: 历史数据获取周期，例如: day,week,month,year
        :param stime: 历史数据获取开始时间
        :param etime: 历史数据获取结束时间
        :return:
        """

        if cycle is not None:
            # 根据传入的监控对象获取性能监控指标id，intervalId为获取数据的周期
            counter_ids = [m.counterId for m in
                           self.obj_perf_mg.QueryAvailablePerfMetric(entity=obj_perfm, intervalId=cycle)]

            # 根据获取到的counterid，生成metric_id
            metric_ids = [vim.PerformanceManager.MetricId(counterId=counter, instance="*") for counter in counter_ids]

            # 根据metric_id，周期获取监控数据
            spec = vim.PerformanceManager.QuerySpec(maxSample=1, entity=obj_perfm, metricId=metric_ids,
                                                    intervalId=cycle, startTime=stime, endTime=etime)
            result_stats = self.obj_perf_mg.QueryStats(querySpec=[spec])

            return result_stats
        else:
            # 根据传入的监控对象获取性能监控指标id，intervalId为获取数据的周期
            counter_ids = [m.counterId for m in self.obj_perf_mg.QueryAvailablePerfMetric(entity=obj_perfm)]

            # 根据获取到的counterid，生成metric_id
            metric_ids = [vim.PerformanceManager.MetricId(counterId=counter, instance="*") for counter in counter_ids]

            # 根据metric_id，周期获取监控数据
            spec = vim.PerformanceManager.QuerySpec(maxSample=1, entity=obj_perfm,
                                                    metricId=metric_ids, startTime=stime, endTime=etime)
            result_stats = self.obj_perf_mg.QueryStats(querySpec=[spec])

            return result_stats

    def proc_time(self):
        """
        处理时间格式
        :return: 返回一个时间元组
        """

        if self.days is not None:
            day = int(self.cycle[self.days])
            return day

        elif self.endtime is not None and self.starttime is not None:

            endtm_utc = self.time_zone(datetime.strptime(self.endtime, "%Y-%m-%d %H:%M:%S")).isoformat(sep="T")
            endtm_iso = datetime.strptime(endtm_utc, "%Y-%m-%dT%H:%M:%S%z")
            starttm_utc = self.time_zone(datetime.strptime(self.starttime, "%Y-%m-%d %H:%M:%S")).isoformat(sep="T")
            starttm_iso = datetime.strptime(starttm_utc, "%Y-%m-%dT%H:%M:%S%z")
            return starttm_iso, endtm_iso

        elif self.starttime is None and self.endtime is None and self.days is None:
            endtm_iso = self.vctime_now
            starttm_iso = endtm_iso - timedelta(seconds=3600)
            return starttm_iso, endtm_iso
        else:
            return False

    def get_realtime_performance_data(self, obj_perfm, realtime, stime, etime):
        """
        获取实时监控数据
        :param obj_perfm: 需要获取性能的对象，例如:物理机，虚拟机
        :param realtime: 获取性能数据的周期，默认是20秒
        :param stime: 采集性能数据的开始时间
        :param etime: 采集性能数据的结束时间
        :return:
        """

        # 根据传入的监控对象获取性能监控指标id，intervalId为获取数据的周期
        counter_ids = [m.counterId for m in self.obj_perf_mg.QueryAvailablePerfMetric(entity=obj_perfm,
                                                                                      intervalId=realtime)]
        # 根据获取到的counterid，生成metric_id
        metric_ids = [vim.PerformanceManager.MetricId(counterId=counter, instance="*") for counter in counter_ids]

        # 根据metric_id，周期获取监控数据
        spec = vim.PerformanceManager.QuerySpec(entity=obj_perfm, metricId=metric_ids, intervalId=realtime,
                                                startTime=stime, endTime=etime)
        result_stats = self.obj_perf_mg.QueryStats(querySpec=[spec])

        return result_stats

    def get_performance_data(self, obj_perfm):
        """
        处理输入时间，并判断获取实时数据或者历史数据
        :param obj_perfm: 需要获取性能的对象，例如:集群，物理机，虚拟机
        :return:
        """

        time_start_end = self.proc_time()
        # 判断监控实体对象是否具备实时监控指标
        realtime_mon = self.obj_perf_mg.QueryPerfProviderSummary(entity=obj_perfm)
        realtime_mon_currentSupported = realtime_mon.currentSupported
        if realtime_mon_currentSupported is True:
            realtime_mon_refreshRate = realtime_mon.refreshRate
            if isinstance(time_start_end, tuple) and len(time_start_end) == 2:
                s_time = time_start_end[0]
                e_time = time_start_end[1]
                if s_time > e_time or e_time > self.vctime_now:
                    return "The time entered is wrong..."
                if e_time < self.g_time:
                    self.his_stat = self.get_hist_performance_data(obj_perfm=obj_perfm, stime=s_time, etime=e_time)
                    return self.his_stat
                elif self.g_time < e_time <= self.vctime_now:
                    if s_time < self.g_time:
                        # 实时数据+历史数据
                        his_diff_time = s_time - self.g_time
                        his_end_time = s_time + timedelta(his_diff_time.seconds)
                        self.his_stat = self.get_hist_performance_data(obj_perfm=obj_perfm, stime=s_time,
                                                                       etime=his_end_time)
                        self.realtime_stat = self.get_realtime_performance_data(obj_perfm, realtime_mon_refreshRate,
                                                                                self.g_time, e_time)
                        return self.his_stat, self.realtime_stat
                    elif s_time >= self.g_time:
                        # 实时数据
                        self.realtime_stat = self.get_realtime_performance_data(obj_perfm, realtime_mon_refreshRate,
                                                                                s_time, e_time)
                        return self.realtime_stat
        elif realtime_mon_currentSupported is False:
            if isinstance(time_start_end, tuple) and len(time_start_end) == 2:
                s_time = time_start_end[0]
                e_time = time_start_end[1]
                if s_time > e_time or e_time > self.vctime_now:
                    return "The time entered is wrong..."
                if e_time < self.g_time:
                    self.his_stat = self.get_hist_performance_data(obj_perfm=obj_perfm, stime=s_time, etime=e_time)
                    return self.his_stat
            elif type(time_start_end) is int:
                self.his_stat = self.get_hist_performance_data(obj_perfm, time_start_end)
                return self.his_stat
            elif type(time_start_end) is bool:
                return "Parameter error"

def main():
    run = VspherePerformance("127.0.0.1", "administrator@vsphere.local", "Root@123", starttime="0", endtime="0")
    ac = run.get_cluster()
    for i in ac:
        for n in i:
            # print(n)
            print(run.get_performance_data(n))


if __name__ == "__main__":
    main()

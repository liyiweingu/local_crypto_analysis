import { useState, useEffect } from 'react'
import ReactECharts from 'echarts-for-react'
import axios from 'axios'
import './App.css'

const indicatorTooltips = {
  'EMA_5': '5周期指数移动平均线，反映短期价格趋势，对近期价格变化更敏感。',
  'EMA_10': '10周期指数移动平均线，反映中短期价格趋势。',
  'EMA_20': '20周期指数移动平均线，反映中期价格趋势，常作为重要支撑/阻力位。',
  'MACD': '平滑异同移动平均线，通过长短周期EMA的差值，判断趋势的强度和方向。',
  'ADX_14': '平均趋向指数，用于衡量趋势的强度。大于25通常被认为存在明显趋势。',
  'RSI_14': '相对强弱指数，衡量价格上涨和下跌的力度。>70为超买，<30为超卖。',
  'Stoch_K': '随机指标的快线，反映当前价格在过去一段时间价格区间中的位置。',
  'Stoch_D': '随机指标的慢线（K线的移动平均），常与K线交叉产生买卖信号。',
  'Momentum': '动量指标，测量价格变化的速度，正值代表上升动能，负值代表下降动能。',
  'BB_Upper': '布林带上轨，通常由20周期移动平均线加上2倍标准差计算得出，可视作阻力位。',
  'BB_Lower': '布林带下轨，通常由20周期移动平均线减去2倍标准差计算得出，可视作支撑位。',
  'ATR_14': '真实波动幅度，衡量市场波动率的指标，常用于设置合理的止损位。',
  'OBV': '能量潮指标，将上涨日的成交量加上，下跌日的成交量减去，用于观察资金流向。',
  'VOL_MA10': '10周期成交量移动平均线，用于平滑成交量数据，判断成交量是否异常放大。'
};

const renderIndicator = (label, valueKey, tooltipKey) => {
  const tooltipText = indicatorTooltips[tooltipKey] || '无说明';

  return (
    <li key={label}>
      <span className="label">
        {label}:
        <span className="info-icon">
          i<span className="info-tooltip">{tooltipText}</span>
        </span>
      </span>
      <span className="value">{valueKey}</span>
    </li>
  );
};

function App() {
  const [chartData, setChartData] = useState(null)
  const [analysisData, setAnalysisData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [symbol, setSymbol] = useState('BTCUSDT')
  const [interval, setInterval] = useState('1m') // 默认改为最小时间间隔 1m
  const [availableCoins, setAvailableCoins] = useState([]) // 动态币种列表
  const [availableIndicators, setAvailableIndicators] = useState([]) // 动态指标列表

  // 格式化时间戳为 MM-DD HH:mm (支持换行展示以便于对齐时间轴)
  const formatTime = (timestamp) => {
    if (!timestamp) return '';
    const d = new Date(timestamp * 1000);
    const pad = (n) => n.toString().padStart(2, '0');
    return (
      <>
        <div style={{fontWeight: 500, color: '#131722'}}>{pad(d.getHours())}:{pad(d.getMinutes())}</div>
        <div style={{fontSize: '11px'}}>{pad(d.getMonth() + 1)}-{pad(d.getDate())}</div>
      </>
    );
  };

  // 控制新闻显示数量
  const [visibleNewsCount, setVisibleNewsCount] = useState(5)

  const fetchCoins = async () => {
    try {
      const [coinsRes, indRes] = await Promise.all([
        axios.get('/api/admin/coins'),
        axios.get('/api/admin/indicators')
      ])
      setAvailableCoins(coinsRes.data)
      setAvailableIndicators(indRes.data)
      if (coinsRes.data.length > 0 && !coinsRes.data.find(c => c.symbol === symbol)) {
        setSymbol(coinsRes.data[0].symbol)
      }
    } catch (err) {
      console.error('Failed to fetch initial data:', err)
    }
  }

  useEffect(() => {
    fetchCoins()
  }, [])

  const [expandedItems, setExpandedItems] = useState({});

  const toggleExpand = (id) => {
    setExpandedItems(prev => ({
      ...prev,
      [id]: !prev[id]
    }));
  };

  const fetchKlineData = async (targetSymbol, targetInterval) => {
    setLoading(true)
    setError(null)
    try {
      // 同时获取K线数据和分析数据
      const [klineRes, analysisRes] = await Promise.all([
        axios.get(`/api/klines`, {
          params: {
            symbol: targetSymbol,
            interval: targetInterval,
            limit: 150
          }
        }),
        axios.get(`/api/analysis`, {
          params: {
            symbol: targetSymbol,
            interval: targetInterval
          }
        })
      ])
      setChartData(klineRes.data)
      setAnalysisData(analysisRes.data)
      setVisibleNewsCount(5) // 重置为默认展示数量
      setExpandedItems({}) // 重置展开状态
    } catch (err) {
      console.error(err)
      setError(err.response?.data?.detail || err.message || '获取数据失败')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchKlineData(symbol, interval)
  }, [symbol, interval])

  // ECharts 配置项
  const getOption = () => {
    if (!chartData || !chartData.values || chartData.values.length === 0) return {}
    
    // 计算移动平均线
    const calculateMA = (dayCount, data) => {
      const result = []
      for (let i = 0, len = data.length; i < len; i++) {
        if (i < dayCount) {
          result.push('-')
          continue
        }
        let sum = 0
        for (let j = 0; j < dayCount; j++) {
          sum += +data[i - j][1] // 收盘价
        }
        result.push(+(sum / dayCount).toFixed(2))
      }
      return result
    }

    // TradingView 风格配色
    const upColor = '#089981'
    const downColor = '#F23645'
    const lastKline = chartData.values[chartData.values.length - 1];
    const isLastUp = lastKline[1] >= lastKline[0];
    const markLineColor = isLastUp ? upColor : downColor;

    // 交易信号标记点
    const markPointData = [];
    if (chartData.signals && chartData.signals.length > 0) {
      chartData.signals.forEach(sig => {
        // 找到该时间点对应的K线数据
        const idx = chartData.categoryData.indexOf(sig.timestamp);
        if (idx !== -1) {
          const kline = chartData.values[idx];
          // data: [open, close, low, high]
          const low = kline[2];
          const high = kline[3];
          
          if (sig.type === 'bullish') {
            markPointData.push({
              name: sig.name,
              coord: [sig.timestamp, low],
              value: 'B',
              symbol: 'arrow',
              symbolSize: 14,
              symbolOffset: [0, '100%'],
              itemStyle: { color: upColor },
              tooltip: { formatter: `${sig.name}<br/>${sig.desc}` }
            });
          } else if (sig.type === 'bearish') {
            markPointData.push({
              name: sig.name,
              coord: [sig.timestamp, high],
              value: 'S',
              symbol: 'arrow',
              symbolSize: 14,
              symbolRotate: 180,
              symbolOffset: [0, '-100%'],
              itemStyle: { color: downColor },
              tooltip: { formatter: `${sig.name}<br/>${sig.desc}` }
            });
          }
        }
      });
    }

    return {
      backgroundColor: '#FFFFFF',
      tooltip: {
        trigger: 'axis',
        axisPointer: {
          type: 'cross',
          label: {
            backgroundColor: '#2962FF'
          },
          crossStyle: {
            color: '#B2B5BE',
            type: 'dashed'
          }
        },
        backgroundColor: 'transparent',
        borderColor: 'transparent',
        shadowBlur: 0,
        padding: 0,
        textStyle: { color: '#131722' },
        formatter: function (param) {
          const klineData = param.find(p => p.seriesType === 'candlestick');
          const ma5Data = param.find(p => p.seriesName === 'MA5');
          const ma10Data = param.find(p => p.seriesName === 'MA10');
          
          if (!klineData) return '';
          const data = klineData.data;
          // data: [date, open, close, low, high]
          const open = data[1].toFixed(2);
          const close = data[2].toFixed(2);
          const low = data[3].toFixed(2);
          const high = data[4].toFixed(2);
          const isUp = data[2] >= data[1];
          const color = isUp ? upColor : downColor;
          const change = (data[2] - data[1]).toFixed(2);
          const percent = ((change / data[1]) * 100).toFixed(2);
          
          let maHtml = '';
          if (ma5Data || ma10Data) {
            maHtml = `<div style="margin-top: 4px;">`;
            if (ma5Data && ma5Data.data !== '-') {
              maHtml += `<span style="color: #2962FF; margin-right: 12px;">MA5 ${ma5Data.data}</span>`;
            }
            if (ma10Data && ma10Data.data !== '-') {
              maHtml += `<span style="color: #FF6D00;">MA10 ${ma10Data.data}</span>`;
            }
            maHtml += `</div>`;
          }
          
          return `
            <div style="font-family: -apple-system, BlinkMacSystemFont, 'Trebuchet MS', Roboto, Ubuntu, sans-serif; font-size: 13px; font-weight: 500;">
              <div>
                <span style="color: #131722; margin-right: 8px;">${klineData.name}</span>
                <span>O <span style="color: ${color}; margin-right: 8px;">${open}</span></span>
                <span>H <span style="color: ${color}; margin-right: 8px;">${high}</span></span>
                <span>L <span style="color: ${color}; margin-right: 8px;">${low}</span></span>
                <span>C <span style="color: ${color}; margin-right: 8px;">${close}</span></span>
                <span style="color: ${color};">${change > 0 ? '+' : ''}${change} (${percent > 0 ? '+' : ''}${percent}%)</span>
              </div>
              ${maHtml}
            </div>
          `;
        },
        position: function (pos, params, el, elRect, size) {
          return { top: 10, left: 15 };
        }
      },
      legend: {
        show: false
      },
      grid: {
        left: '2%',
        right: '6%',
        bottom: '5%',
        top: '10%',
        containLabel: true
      },
      xAxis: {
        type: 'category',
        data: chartData.categoryData,
        boundaryGap: false,
        axisLine: { lineStyle: { color: '#E0E3EB' } },
        axisLabel: { color: '#787B86', margin: 15 },
        axisTick: { show: false },
        splitLine: { show: true, lineStyle: { color: '#E0E3EB', type: 'solid', opacity: 0.6 } },
        min: 'dataMin',
        max: 'dataMax'
      },
      yAxis: {
        position: 'right',
        scale: true,
        splitArea: { show: false },
        axisLine: { show: false },
        axisLabel: { color: '#787B86', inside: false, formatter: '{value}' },
        axisTick: { show: false },
        splitLine: { show: true, lineStyle: { color: '#E0E3EB', type: 'solid', opacity: 0.6 } }
      },
      dataZoom: [
        {
          type: 'inside',
          start: 70,
          end: 100
        }
      ],
      series: [
        {
          name: 'K线',
          type: 'candlestick',
          data: chartData.values,
          itemStyle: {
            color: upColor,
            color0: downColor,
            borderColor: upColor,
            borderColor0: downColor
          },
          markLine: {
            symbol: ['none', 'none'],
            data: [
              {
                yAxis: lastKline[1], // 收盘价
                label: {
                  position: 'end',
                  backgroundColor: markLineColor,
                  color: '#fff',
                  padding: [4, 6],
                  borderRadius: 4,
                  formatter: '{c}'
                },
                lineStyle: {
                  color: markLineColor,
                  type: 'dashed'
                }
              }
            ],
            animation: false
          },
          markPoint: {
            data: markPointData,
            label: {
              formatter: '{c}',
              color: '#fff',
              fontSize: 10,
              fontWeight: 'bold'
            }
          }
        },
        {
          name: 'MA5',
          type: 'line',
          data: calculateMA(5, chartData.values),
          smooth: true,
          showSymbol: false,
          lineStyle: { width: 1.5, opacity: 0.8, color: '#2962FF' },
          itemStyle: { color: '#2962FF' }
        },
        {
          name: 'MA10',
          type: 'line',
          data: calculateMA(10, chartData.values),
          smooth: true,
          showSymbol: false,
          lineStyle: { width: 1.5, opacity: 0.8, color: '#FF6D00' },
          itemStyle: { color: '#FF6D00' }
        }
      ]
    }
  }

  // 计算是否需要显示“展示更多”按钮
  const hasMoreNews = analysisData?.news && visibleNewsCount < analysisData.news.length;
  const hasMoreWhales = analysisData?.whale_alerts && visibleNewsCount < analysisData.whale_alerts.length;
  const showLoadMoreBtn = hasMoreNews || hasMoreWhales;

  return (
    <div className="app-container">
      <header className="header">
        <h1>加密货币趋势预测看板</h1>
        <div className="controls">
          <div className="interval-controls">
            {[
              { label: '1m', value: '1m' },
              { label: '15m', value: '15m' },
              { label: '1h', value: '1h' },
              { label: '4h', value: '4h' },
              { label: '24h', value: '1d' },
              { label: '7d', value: '1w' },
              { label: '30d', value: '1M' }
            ].map(item => (
              <button 
                key={item.value} 
                className={`interval-btn ${interval === item.value ? 'active' : ''}`}
                onClick={() => setInterval(item.value)}
              >
                {item.label}
              </button>
            ))}
          </div>
          <div className="symbol-control">
            <label>选择币种: </label>
            <select value={symbol} onChange={(e) => setSymbol(e.target.value)}>
              {availableCoins.map(c => (
                <option key={c.symbol} value={c.symbol}>{c.name}</option>
              ))}
            </select>
          </div>
          <a href="/admin" className="admin-link">后台管理</a>
        </div>
      </header>
      
      <main className="main-content">
        {loading && <div className="loading">加载数据中...</div>}
        {error && <div className="error">错误: {error}</div>}
        {!loading && !error && chartData && (
          <div className="dashboard">
            <div className="chart-wrapper">
              <ReactECharts 
                option={getOption()} 
                style={{ height: '600px', width: '100%' }}
                notMerge={true}
              />
            </div>
            
            {analysisData && analysisData.guide && (
              <div className="analysis-panel">
                <h2>智能交易分析指南</h2>
                
                <div className="status-cards">
                  <div className="card">
                    <span className="card-label">市场状态</span>
                    <span className={`card-value ${analysisData.guide.status === '上升' ? 'bullish' : analysisData.guide.status === '下跌' ? 'bearish' : 'neutral'}`}>
                      {analysisData.guide.status}
                    </span>
                  </div>
                  <div className="card">
                    <span className="card-label">操作建议</span>
                    <span className={`card-value action-${analysisData.guide.action}`}>
                      {analysisData.guide.action}
                    </span>
                  </div>
                  <div className="card">
                    <span className="card-label">综合评分</span>
                    <span className={`card-value ${analysisData.guide.total_score > 0 ? 'bullish' : 'bearish'}`}>
                      {analysisData.guide.total_score}
                    </span>
                  </div>
                  <div className="card">
                    <span className="card-label">情绪得分</span>
                    <span className={`card-value ${analysisData.sentiment_score > 0 ? 'bullish' : 'bearish'}`}>
                      {analysisData.sentiment_score}
                    </span>
                  </div>
                </div>

                <div className="risk-warning">
                  <h3>风险与策略提示</h3>
                  <ul className="strategy-list">
                    <li><span className="label">24h建议止损价:</span> <span className="value">{analysisData.guide.stop_loss}</span></li>
                    <li><span className="label">24h建议止盈价:</span> <span className="value">{analysisData.guide.take_profit}</span></li>
                    <li><span className="label">市场状态:</span> <span className="value">{analysisData.guide.status}</span> <span className="reason">({analysisData.guide.status_reason})</span></li>
                    <li><span className="label">操作建议:</span> <span className="value">{analysisData.guide.action}</span> <span className="reason">({analysisData.guide.action_reason})</span></li>
                    <li><span className="label">综合评分:</span> <span className="value">{analysisData.guide.total_score}</span> <span className="reason">({analysisData.guide.total_score_process})</span></li>
                    <li><span className="label">情绪得分:</span> <span className="value">{analysisData.guide.sentiment_score}</span> <span className="reason">({analysisData.guide.sentiment_score_process})</span></li>
                    <li><span className="label">系统风险提示:</span> <span className="value risk-text">{analysisData.guide.risk}</span></li>
                  </ul>
                </div>

                <div className="indicators-detail">
                  <h3>当前技术指标明细</h3>
                  {chartData.indicators && (
                    <div className="indicators-grid">
                      <div className="indicator-group">
                        <h4>趋势指标</h4>
                        <ul>
                          {renderIndicator('EMA_5', chartData.indicators.trend?.EMA_5?.[chartData.indicators.trend.EMA_5.length - 1]?.toFixed(2) || '-', 'EMA_5')}
                          {renderIndicator('EMA_10', chartData.indicators.trend?.EMA_10?.[chartData.indicators.trend.EMA_10.length - 1]?.toFixed(2) || '-', 'EMA_10')}
                          {renderIndicator('EMA_20', chartData.indicators.trend?.EMA_20?.[chartData.indicators.trend.EMA_20.length - 1]?.toFixed(2) || '-', 'EMA_20')}
                          {renderIndicator('MACD', chartData.indicators.trend?.MACD?.[chartData.indicators.trend.MACD.length - 1]?.toFixed(2) || '-', 'MACD')}
                          {renderIndicator('ADX_14', chartData.indicators.trend?.ADX?.[chartData.indicators.trend.ADX.length - 1]?.toFixed(2) || '-', 'ADX_14')}
                        </ul>
                      <div className="indicator-group">
                        <h4>自定义指标</h4>
                        <ul>
                          {availableIndicators.length === 0 ? (
                            <li><span className="label" style={{display: 'block'}}>暂无自定义指标</span></li>
                          ) : (
                            availableIndicators.map(ind => {
                              const arr = chartData.indicators.custom?.[ind.name];
                              const val = arr ? arr[arr.length - 1] : undefined;
                              const displayVal = val !== undefined && val !== null ? Number(val).toFixed(2) : '-';
                              return (
                                <li key={ind.id}>
                                  <span className="label">
                                    {ind.name}:
                                    <span className="info-icon">
                                      i<span className="info-tooltip">{ind.description}</span>
                                    </span>
                                  </span>
                                  <span className="value">{displayVal}</span>
                                </li>
                              )
                            })
                          )}
                        </ul>
                      </div>
                    </div>
                      <div className="indicator-group">
                        <h4>动量指标</h4>
                        <ul>
                          {renderIndicator('RSI_14', chartData.indicators.momentum?.RSI_14?.[chartData.indicators.momentum.RSI_14.length - 1]?.toFixed(2) || '-', 'RSI_14')}
                          {renderIndicator('Stoch_K', chartData.indicators.momentum?.STOCH_k?.[chartData.indicators.momentum.STOCH_k.length - 1]?.toFixed(2) || '-', 'Stoch_K')}
                          {renderIndicator('Stoch_D', chartData.indicators.momentum?.STOCH_d?.[chartData.indicators.momentum.STOCH_d.length - 1]?.toFixed(2) || '-', 'Stoch_D')}
                          {renderIndicator('Momentum', chartData.indicators.momentum?.MOM_10?.[chartData.indicators.momentum.MOM_10.length - 1]?.toFixed(2) || '-', 'Momentum')}
                        </ul>
                      </div>
                      <div className="indicator-group">
                        <h4>波动 & 成交指标</h4>
                        <ul>
                          {renderIndicator('BB Upper', chartData.indicators.volatility?.BB_upper?.[chartData.indicators.volatility.BB_upper.length - 1]?.toFixed(2) || '-', 'BB_Upper')}
                          {renderIndicator('BB Lower', chartData.indicators.volatility?.BB_lower?.[chartData.indicators.volatility.BB_lower.length - 1]?.toFixed(2) || '-', 'BB_Lower')}
                          {renderIndicator('ATR_14', chartData.indicators.volatility?.ATR_14?.[chartData.indicators.volatility.ATR_14.length - 1]?.toFixed(2) || '-', 'ATR_14')}
                          {renderIndicator('OBV', chartData.indicators.volume?.OBV?.[chartData.indicators.volume.OBV.length - 1]?.toFixed(2) || '-', 'OBV')}
                          {renderIndicator('Vol MA10', chartData.indicators.volume?.VOL_MA10?.[chartData.indicators.volume.VOL_MA10.length - 1]?.toFixed(2) || '-', 'VOL_MA10')}
                        </ul>
                      </div>
                    </div>
                  )}
                </div>

                      <div className="news-and-whales">
                        <div className="news-section">
                          <h3>实时相关新闻情绪</h3>
                          {analysisData.news && analysisData.news.length > 0 ? (
                            <div className="timeline-container">
                              {analysisData.news.slice(0, visibleNewsCount).map((item, idx) => (
                                <div key={`news-${idx}`} className="timeline-item">
                                  <div className="timeline-time">{formatTime(item.timestamp)}</div>
                                  <div className="timeline-marker"></div>
                                  <div className="timeline-content news-content">
                                    <span className={`sentiment-badge sentiment-${item.sentiment_res.sentiment}`}>
                                      {item.sentiment_res.sentiment === 'positive' ? '利好' : item.sentiment_res.sentiment === 'negative' ? '利空' : '中性'}
                                    </span>
                                    <div className="timeline-content-wrapper">
                                      <a 
                                        href={item.link} 
                                        target="_blank" 
                                        rel="noreferrer" 
                                        title={item.title}
                                        className={expandedItems[`news-${idx}`] ? 'expanded' : ''}
                                      >
                                        {item.title}
                                      </a>
                                      {item.title.length > 50 && (
                                        <button 
                                          className="expand-btn" 
                                          onClick={() => toggleExpand(`news-${idx}`)}
                                        >
                                          {expandedItems[`news-${idx}`] ? '收起' : '展开全文'}
                                        </button>
                                      )}
                                    </div>
                                  </div>
                                </div>
                              ))}
                            </div>
                          ) : (
                            <p className="no-news">暂无最新相关新闻</p>
                          )}
                        </div>

                        <div className="news-section whale-section">
                          <h3>🐳 巨鲸动态跟踪 (Whale Alert)</h3>
                          {analysisData.whale_alerts && analysisData.whale_alerts.length > 0 ? (
                            <div className="timeline-container">
                              {analysisData.whale_alerts.slice(0, visibleNewsCount).map((item, idx) => (
                                <div key={`whale-${idx}`} className="timeline-item">
                                  <div className="timeline-time">{formatTime(item.timestamp)}</div>
                                  <div className="timeline-marker whale-marker"></div>
                                  <div className="timeline-content whale-content">
                                    <span className={`sentiment-badge sentiment-${item.sentiment_res.sentiment}`}>
                                      {item.sentiment_res.sentiment === 'positive' ? '利多' : item.sentiment_res.sentiment === 'negative' ? '利空' : '转移'}
                                    </span>
                                    <div className="timeline-content-wrapper">
                                      <a 
                                        href={item.link} 
                                        target="_blank" 
                                        rel="noreferrer" 
                                        title={item.title}
                                        className={expandedItems[`whale-${idx}`] ? 'expanded' : ''}
                                      >
                                        {item.title}
                                      </a>
                                      {item.title.length > 50 && (
                                        <button 
                                          className="expand-btn" 
                                          onClick={() => toggleExpand(`whale-${idx}`)}
                                        >
                                          {expandedItems[`whale-${idx}`] ? '收起' : '展开全文'}
                                        </button>
                                      )}
                                    </div>
                                  </div>
                                </div>
                              ))}
                            </div>
                          ) : (
                            <p className="no-news">当前币种暂无巨鲸转移记录</p>
                          )}
                        </div>
                      </div>

                      {showLoadMoreBtn && (
                        <div className="load-more-container">
                          <button 
                            className="load-more-btn"
                            onClick={() => setVisibleNewsCount(prev => prev + 10)}
                          >
                            展示更多 ({Math.max(analysisData.news?.length || 0, analysisData.whale_alerts?.length || 0) - visibleNewsCount})
                          </button>
                        </div>
                      )}
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  )
}

export default App

import React, { useState, useEffect } from 'react';
import axios from 'axios';
import './Admin.css';

function Admin() {
  const [coins, setCoins] = useState([]);
  const [indicators, setIndicators] = useState([]);
  const [sources, setSources] = useState([]);
  const [prompts, setPrompts] = useState([]);
  const [aiConfig, setAiConfig] = useState({ api_key: '', base_url: '', model_name: '' });

  const [newCoin, setNewCoin] = useState({ symbol: '', name: '' });
  const [newIndicator, setNewIndicator] = useState({ name: '', calc_method: '', description: '' });
  const [newSource, setNewSource] = useState({ name: '', url: '' });

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const [coinsRes, indRes, srcRes, promptsRes, aiConfigRes] = await Promise.all([
        axios.get('/api/admin/coins'),
        axios.get('/api/admin/indicators'),
        axios.get('/api/admin/sources'),
        axios.get('/api/admin/prompts'),
        axios.get('/api/admin/ai_config')
      ]);
      setCoins(coinsRes.data);
      setIndicators(indRes.data);
      setSources(srcRes.data);
      setPrompts(promptsRes.data);
      setAiConfig(aiConfigRes.data);
    } catch (err) {
      console.error('Fetch data error:', err);
    }
  };

  const handleAddCoin = async (e) => {
    e.preventDefault();
    try {
      await axios.post('/api/admin/coins', newCoin);
      setNewCoin({ symbol: '', name: '' });
      fetchData();
    } catch (err) {
      alert(err.response?.data?.detail || 'Error adding coin');
    }
  };

  const handleDeleteCoin = async (symbol) => {
    try {
      await axios.delete(`/api/admin/coins/${symbol}`);
      fetchData();
    } catch (err) {
      console.error(err);
    }
  };

  const handleAddIndicator = async (e) => {
    e.preventDefault();
    try {
      await axios.post('/api/admin/indicators', newIndicator);
      setNewIndicator({ name: '', calc_method: '', description: '' });
      fetchData();
    } catch (err) {
      alert(err.response?.data?.detail || 'Error adding indicator');
    }
  };

  const handleDeleteIndicator = async (id) => {
    try {
      await axios.delete(`/api/admin/indicators/${id}`);
      fetchData();
    } catch (err) {
      console.error(err);
    }
  };

  const handleAddSource = async (e) => {
    e.preventDefault();
    try {
      await axios.post('/api/admin/sources', newSource);
      setNewSource({ name: '', url: '' });
      fetchData();
    } catch (err) {
      alert(err.response?.data?.detail || 'Error adding source');
    }
  };

  const handleDeleteSource = async (id) => {
    try {
      await axios.delete(`/api/admin/sources/${id}`);
      fetchData();
    } catch (err) {
      console.error(err);
    }
  };

  const handleSavePrompts = async (e) => {
    e.preventDefault();
    try {
      const promptsDict = {};
      prompts.forEach(p => promptsDict[p.key] = p.value);
      await axios.put('/api/admin/prompts', { prompts: promptsDict });
      alert('提示词保存成功');
    } catch (err) {
      alert(err.response?.data?.detail || 'Error saving prompts');
    }
  };

  const handleSaveAiConfig = async (e) => {
    e.preventDefault();
    try {
      await axios.put('/api/admin/ai_config', { configs: aiConfig });
      alert('AI配置保存成功');
    } catch (err) {
      alert(err.response?.data?.detail || 'Error saving AI config');
    }
  };

  return (
    <div className="admin-container">
      <header className="admin-header">
        <h1>管理后台</h1>
        <a href="/" className="back-link">返回看板</a>
      </header>

      <div className="admin-content">
        {/* 币种管理 */}
        <section className="admin-section">
          <h2>1. 币种管理</h2>
          <p className="section-desc">添加币种后，看板下拉列表将同步更新。如果本地无数据，首次查询将自动从币安实时获取走势。</p>
          
          <form className="admin-form" onSubmit={handleAddCoin}>
            <input 
              type="text" 
              placeholder="Symbol (例如: DOGEUSDT)" 
              value={newCoin.symbol} 
              onChange={e => setNewCoin({...newCoin, symbol: e.target.value})} 
              required 
            />
            <input 
              type="text" 
              placeholder="显示名称 (例如: DOGE/USDT)" 
              value={newCoin.name} 
              onChange={e => setNewCoin({...newCoin, name: e.target.value})} 
              required 
            />
            <button type="submit">添加币种</button>
          </form>

          <table className="admin-table">
            <thead>
              <tr>
                <th>Symbol</th>
                <th>显示名称</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              {coins.map(c => (
                <tr key={c.symbol}>
                  <td>{c.symbol}</td>
                  <td>{c.name}</td>
                  <td>
                    <button className="delete-btn" onClick={() => handleDeleteCoin(c.symbol)}>删除</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>

        {/* 技术指标管理 */}
        <section className="admin-section">
          <h2>2. 自定义技术指标管理</h2>
          <p className="section-desc">输入指标名称和对应的 pandas-ta 计算方法。例如名称：<code>SMA_30</code>，计算方法：<code>df.ta.sma(length=30)</code></p>
          
          <form className="admin-form" onSubmit={handleAddIndicator}>
            <input 
              type="text" 
              placeholder="指标名称 (如 SMA_30)" 
              value={newIndicator.name} 
              onChange={e => setNewIndicator({...newIndicator, name: e.target.value})} 
              required 
            />
            <input 
              type="text" 
              placeholder="计算方法 (如 df.ta.sma(length=30))" 
              value={newIndicator.calc_method} 
              onChange={e => setNewIndicator({...newIndicator, calc_method: e.target.value})} 
              required 
            />
            <input 
              type="text" 
              placeholder="指标说明弹窗文案" 
              value={newIndicator.description} 
              onChange={e => setNewIndicator({...newIndicator, description: e.target.value})} 
              required 
            />
            <button type="submit">添加指标</button>
          </form>

          <table className="admin-table">
            <thead>
              <tr>
                <th>名称</th>
                <th>计算方法</th>
                <th>说明</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              {indicators.map(i => (
                <tr key={i.id}>
                  <td>{i.name}</td>
                  <td><code>{i.calc_method}</code></td>
                  <td>{i.description}</td>
                  <td>
                    <button className="delete-btn" onClick={() => handleDeleteIndicator(i.id)}>删除</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>

        {/* 新闻源管理 */}
        <section className="admin-section">
          <h2>3. 新闻源管理</h2>
          <p className="section-desc">
            添加新闻等内容的获取渠道。
            <br />
            - 如果添加外部网站如 <code>ChainCatcher</code>，URL 请输入对应的网址。
            <br />
            - 如果要使用本地库中的文章内容作为新闻源，URL 请输入：<code>local://db</code>
          </p>
          
          <form className="admin-form" onSubmit={handleAddSource}>
            <input 
              type="text" 
              placeholder="新闻源名称 (如 Coindesk)" 
              value={newSource.name} 
              onChange={e => setNewSource({...newSource, name: e.target.value})} 
              required 
            />
            <input 
              type="url" 
              placeholder="网站 URL" 
              value={newSource.url} 
              onChange={e => setNewSource({...newSource, url: e.target.value})} 
              required 
            />
            <button type="submit">添加新闻源</button>
          </form>

          <table className="admin-table">
            <thead>
              <tr>
                <th>来源名称</th>
                <th>URL</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              {sources.map(s => (
                <tr key={s.id}>
                  <td>{s.name}</td>
                  <td><a href={s.url} target="_blank" rel="noreferrer">{s.url}</a></td>
                  <td>
                    <button className="delete-btn" onClick={() => handleDeleteSource(s.id)}>删除</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>

        {/* 提示词管理 */}
        <section className="admin-section">
          <h2>4. 提示词与话术管理</h2>
          <p className="section-desc">自定义主看板上的动态分析话术。大括号 <code>{`{}`}</code> 中的内容为变量，请勿随意修改变量名。</p>
          
          <form className="prompts-form" onSubmit={handleSavePrompts}>
            {prompts.map(p => (
              <div key={p.key} className="prompt-item">
                <label className="prompt-label">
                  {p.key} <span className="prompt-desc">({p.description})</span>
                </label>
                <textarea 
                  className="prompt-textarea"
                  value={p.value}
                  onChange={(e) => {
                    const newPrompts = prompts.map(item => item.key === p.key ? {...item, value: e.target.value} : item);
                    setPrompts(newPrompts);
                  }}
                />
              </div>
            ))}
            <button type="submit">保存所有提示词</button>
          </form>
        </section>

        {/* AI 接口配置管理 */}
        <section className="admin-section">
          <h2>5. AI 接口配置</h2>
          <p className="section-desc">配置项目中间环节（如情绪分析、文本处理）所使用的大语言模型 API。默认兼容 OpenAI 格式接口。</p>
          
          <form className="admin-form ai-config-form" onSubmit={handleSaveAiConfig}>
            <div className="form-group">
              <label>API Key (必填):</label>
              <input 
                type="password" 
                placeholder="sk-..." 
                value={aiConfig.api_key || ''} 
                onChange={e => setAiConfig({...aiConfig, api_key: e.target.value})} 
              />
            </div>
            <div className="form-group">
              <label>Base URL:</label>
              <input 
                type="text" 
                placeholder="https://api.openai.com/v1" 
                value={aiConfig.base_url || ''} 
                onChange={e => setAiConfig({...aiConfig, base_url: e.target.value})} 
              />
            </div>
            <div className="form-group">
              <label>Model Name:</label>
              <input 
                type="text" 
                placeholder="gpt-3.5-turbo" 
                value={aiConfig.model_name || ''} 
                onChange={e => setAiConfig({...aiConfig, model_name: e.target.value})} 
              />
            </div>
            <button type="submit">保存 AI 配置</button>
          </form>
        </section>

      </div>
    </div>
  );
}

export default Admin;
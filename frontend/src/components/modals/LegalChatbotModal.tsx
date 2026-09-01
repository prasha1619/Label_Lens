import React, { useState } from 'react';
import { X, Send, Bot, User as UserIcon, Sparkles } from 'lucide-react';
import { useAuth } from '../../auth/AuthContext';

interface LegalChatbotModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const LegalChatbotModal: React.FC<LegalChatbotModalProps> = ({ isOpen, onClose }) => {
  const { user } = useAuth();
  const [input, setInput] = useState('');
  const [messages, setMessages] = useState([
    {
      sender: 'bot',
      text: `नमस्ते ${user?.full_name ? user.full_name.split(' ')[0] : 'Inspector'}! I am your AI Legal Metrology Assistant. Ask me anything about Rule 6 declarations, MRP regulations, font size guidelines, or penalty clauses.`,
    },
  ]);


  if (!isOpen) return null;

  const handleSend = (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim()) return;

    const userText = input;
    const newMessages = [...messages, { sender: 'user', text: userText }];
    setMessages(newMessages);
    setInput('');

    // Generate intelligent Legal Metrology response
    setTimeout(() => {
      let reply = "Under Legal Metrology (PC) Rules 2011, all mandatory declarations must be printed in the prescribed font size matching the principal display panel area.";
      const lower = userText.toLowerCase();
      if (lower.includes('mrp') || lower.includes('price')) {
        reply = "MRP must be declared inclusive of all taxes, e.g., 'MRP ₹ xxx.xx (incl. of all taxes)'. Unit Sale Price (USP) is also mandatory for commodities with net weight above 100g/100ml under Rule 6(1)(e).";
      } else if (lower.includes('font') || lower.includes('height') || lower.includes('size')) {
        reply = "For Principal Display Panel (PDP) area between 50 cm² to 200 cm², minimum numeral height is 2.0 mm (1.0 mm for blown/moulded). For PDP > 200 cm² up to 1000 cm², minimum numeral height is 4.0 mm.";
      } else if (lower.includes('penalty') || lower.includes('fine') || lower.includes('violation')) {
        reply = "Under Section 36 of the Legal Metrology Act, 2009, non-compliance with packaging rules attracts a penalty of up to ₹25,000 for the first offence, ₹50,000 for second, and up to ₹1,00,000 or imprisonment for subsequent offences.";
      }

      setMessages((prev) => [...prev, { sender: 'bot', text: reply }]);
    }, 600);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm animate-fadeIn">
      <div className="relative w-full max-w-lg rounded-2xl bg-[#0e1533] border border-[#232f58] shadow-2xl overflow-hidden h-[550px] flex flex-col">
        {/* Header */}
        <div className="px-5 py-4 bg-[#121a3b] border-b border-[#202b52] flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-purple-600 to-indigo-600 flex items-center justify-center text-white shadow-md">
              <Bot className="w-5 h-5" />
            </div>
            <div>
              <div className="text-sm font-bold text-white flex items-center gap-1.5">
                <span>LabelLens AI Assistant</span>
                <Sparkles className="w-3.5 h-3.5 text-purple-400" />
              </div>
              <div className="text-[10px] text-emerald-400 flex items-center gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
                <span>Online &bull; Legal Metrology Expert</span>
              </div>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 text-slate-400 hover:text-white rounded-lg hover:bg-slate-800/60 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Message Area */}
        <div className="flex-1 p-4 overflow-y-auto space-y-3 scrollbar-thin">
          {messages.map((m, idx) => (
            <div
              key={idx}
              className={`flex items-start space-x-2.5 ${
                m.sender === 'user' ? 'flex-row-reverse space-x-reverse' : ''
              }`}
            >
              <div
                className={`w-7 h-7 rounded-lg flex items-center justify-center text-xs flex-shrink-0 ${
                  m.sender === 'user'
                    ? 'bg-purple-600 text-white'
                    : 'bg-[#18234c] text-purple-300 border border-[#28376b]'
                }`}
              >
                {m.sender === 'user' ? <UserIcon className="w-4 h-4" /> : <Bot className="w-4 h-4" />}
              </div>
              <div
                className={`p-3 rounded-2xl text-xs max-w-[80%] leading-relaxed ${
                  m.sender === 'user'
                    ? 'bg-gradient-to-r from-purple-600 to-indigo-600 text-white rounded-tr-none'
                    : 'bg-[#141d3e] text-slate-200 border border-[#212c54] rounded-tl-none'
                }`}
              >
                {m.text}
              </div>
            </div>
          ))}
        </div>

        {/* Prompt Input */}
        <form onSubmit={handleSend} className="p-3 bg-[#111938] border-t border-[#202b52] flex items-center space-x-2">
          <input
            type="text"
            placeholder="Ask about rules, font sizes, MRP, penalties..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            className="flex-1 px-3.5 py-2 bg-[#172146] border border-[#273668] rounded-xl text-xs text-white placeholder-slate-400 focus:outline-none focus:border-purple-500"
          />
          <button
            type="submit"
            className="p-2.5 rounded-xl bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white shadow-lg transition-all"
          >
            <Send className="w-4 h-4" />
          </button>
        </form>
      </div>
    </div>
  );
};

const axios = require('axios');

async function test() {
    try {
        const res = await axios.post('http://127.0.0.1:8000/api/v1/auth/login', {
            email: 'employee@demo.com',
            password: 'demo123'
        });
        console.log('LOGIN SUCCESS:', res.data.access_token);
        
        const products = await axios.get('http://127.0.0.1:8000/api/v1/products', {
            headers: {
                Authorization: `Bearer ${res.data.access_token}`
            }
        });
        console.log('PRODUCTS SUCCESS:', products.data.length, 'items');

        const logout = await axios.get('http://127.0.0.1:8000/api/v1/auth/me', {
            headers: {
                Authorization: `Bearer ${res.data.access_token}`
            }
        });
        console.log('AUTH ME SUCCESS:', logout.data.user.email);
    } catch (err) {
        console.log('ERROR:', err.response ? err.response.data : err.message);
    }
}
test();

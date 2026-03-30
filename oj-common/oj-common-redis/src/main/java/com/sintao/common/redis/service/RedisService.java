package com.sintao.common.redis.service;

import com.alibaba.fastjson2.JSON;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.data.redis.core.ValueOperations;
import org.springframework.stereotype.Component;
import org.springframework.util.CollectionUtils;

import java.util.ArrayList;
import java.util.Collection;
import java.util.List;
import java.util.Map;
import java.util.concurrent.TimeUnit;

@Component
public class RedisService {

    @Autowired
    public RedisTemplate redisTemplate;

    //************************ 操作key ***************************

    /**
     * 判断 key是否存在
     *
     * @param key �?     * @return true 存在 false不存�?     */
    public Boolean hasKey(String key) {
        return redisTemplate.hasKey(key);
    }


    /**
     * 设置有效时间
     *
     * @param key     Redis�?     * @param timeout 超时时间
     * @return true=设置成功；false=设置失败
     */
    public boolean expire(final String key, final long timeout) {
        return expire(key, timeout, TimeUnit.SECONDS);
    }

    /**
     * 设置有效时间
     *
     * @param key     Redis�?     * @param timeout 超时时间
     * @param unit    时间单位
     * @return true=设置成功；false=设置失败
     */
    public boolean expire(final String key, final long timeout, final TimeUnit unit) {
        return redisTemplate.expire(key, timeout, unit);
    }

    /**
     * 获取剩余有效时间
     *
     * @param key  Redis�?     * @param unit 时间单位
     * @return 剩余有效时间
     */
    public Long getExpire(final String key, final TimeUnit unit) {
        return redisTemplate.getExpire(key, unit);
    }

    /**
     * 删除单个对象
     *
     * @param key
     */
    public boolean deleteObject(final String key) {
        return redisTemplate.delete(key);
    }

    //************************ 操作String类型 ***************************

    /**
     * 缓存基本的对象，Integer、String、实体类�?     *
     * @param key   缓存的键�?     * @param value 缓存的�?     */
    public <T> void setCacheObject(final String key, final T value) {
        redisTemplate.opsForValue().set(key, value);
    }

    /**
     * 缓存基本的对象，Integer、String、实体类�?     *
     * @param key      缓存的键�?     * @param value    缓存的�?     * @param timeout  时间
     * @param timeUnit 时间颗粒�?     */
    public <T> void setCacheObject(final String key, final T value, final Long timeout, final TimeUnit timeUnit) {
        redisTemplate.opsForValue().set(key, value, timeout, timeUnit);
    }

    public <T> boolean setCacheObjectIfAbsent(final String key,
                                              final T value,
                                              final Long timeout,
                                              final TimeUnit timeUnit) {
        Boolean success = redisTemplate.opsForValue().setIfAbsent(key, value, timeout, timeUnit);
        return Boolean.TRUE.equals(success);
    }

    /**
     * 获得缓存的基本对象�?     *
     * @param key 缓存键�?     * @return 缓存键值对应的数据
     */
    public <T> T getCacheObject(final String key, Class<T> clazz) {
        ValueOperations<String, T> operation = redisTemplate.opsForValue();
        T t = operation.get(key);
        if (t instanceof String) {
            return t;
        }
        return JSON.parseObject(String.valueOf(t), clazz);
    }

    public <T> List<T> multiGet(final List<String> keyList, Class<T> clazz) {
        List list = redisTemplate.opsForValue().multiGet(keyList);
        if (list == null || list.size() <= 0) {
            return null;
        }
        List<T> result = new ArrayList<>();
        for (Object o : list) {
            result.add(JSON.parseObject(String.valueOf(o), clazz));
        }
        return result;
    }

    public <K, V> void multiSet(Map<? extends K, ? extends V> map) {
        redisTemplate.opsForValue().multiSet(map);
    }

    /**
     * 计数加一
     *
     * @param key
     * @return
     */
    public Long increment(final String key) {
        return redisTemplate.opsForValue().increment(key);
    }

    //*************** 操作list结构 ****************

    /**
     * 获取list中存储数据数�?     *
     * @param key
     * @return
     */
    public Long getListSize(final String key) {
        return redisTemplate.opsForList().size(key);
    }

    /**
     * 获取list中指定范围数�?     *
     * @param key
     * @param start
     * @param end
     * @param clazz
     * @param <T>
     * @return
     */
    public <T> List<T> getCacheListByRange(final String key, long start, long end, Class<T> clazz) {
        List range = redisTemplate.opsForList().range(key, start, end);
        if (CollectionUtils.isEmpty(range)) {
            return null;
        }
        return JSON.parseArray(JSON.toJSONString(range), clazz);
    }

    /**
     * 底层使用list结构存储数据(尾插 批量插入)
     */
    public <T> Long rightPushAll(final String key, Collection<T> list) {
        return redisTemplate.opsForList().rightPushAll(key, list);
    }

    /**
     * 底层使用list结构存储数据(头插)
     */
    public <T> Long leftPushForList(final String key, T value) {
        return redisTemplate.opsForList().leftPush(key, value);
    }

    /**
     * 底层使用list结构,删除指定数据
     */
    public <T> Long removeForList(final String key, T value) {
        return redisTemplate.opsForList().remove(key, 1L, value);
    }


    public <T> Long indexOfForList(final String key, T value) {
        return redisTemplate.opsForList().indexOf(key, value);
    }

    public <T> T indexForList(final String key, long index, Class<T> clazz) {
        Object t = redisTemplate.opsForList().index(key, index);
        return JSON.parseObject(String.valueOf(t), clazz);
    }


    //************************ 操作Hash类型 ***************************
    public <T> T getCacheMapValue(final String key, final String hKey, Class<T> clazz) {
        Object cacheMapValue = redisTemplate.opsForHash().get(key, hKey);
        if (cacheMapValue != null) {
            return JSON.parseObject(String.valueOf(cacheMapValue), clazz);
        }
        return null;
    }


    /**
     * 获取多个Hash中的数据
     *
     * @param key   Redis�?     * @param hKeys Hash键集�?     * @param clazz 待转换对象类�?     * @param <T>   泛型
     * @return Hash对象集合
     */
    public <T> List<T> getMultiCacheMapValue(final String key, final Collection<String> hKeys, Class<T> clazz) {
        List list = redisTemplate.opsForHash().multiGet(key, hKeys);
        List<T> result = new ArrayList<>();
        for (Object item : list) {
            result.add(JSON.parseObject(JSON.toJSONString(item), clazz));
        }

        return result;
    }

    /**
     * 往Hash中存入数�?     *
     * @param key   Redis�?     * @param hKey  Hash�?     * @param value �?     */
    public <T> void setCacheMapValue(final String key, final String hKey, final T value) {
        redisTemplate.opsForHash().put(key, hKey, value);
    }

    /**
     * 缓存Map
     *
     * @param key
     * @param dataMap
     */
    public <K, T> void setCacheMap(final String key, final Map<K, T> dataMap) {
        if (dataMap != null) {
            redisTemplate.opsForHash().putAll(key, dataMap);
        }
    }

    public <K, T> void setCacheMap(final String key,
                                   final Map<K, T> dataMap,
                                   final Long timeout,
                                   final TimeUnit timeUnit) {
        if (dataMap != null) {
            redisTemplate.opsForHash().putAll(key, dataMap);
            if (timeout != null && timeUnit != null) {
                redisTemplate.expire(key, timeout, timeUnit);
            }
        }
    }

    public Long deleteCacheMapValue(final String key, final String hKey) {
        return redisTemplate.opsForHash().delete(key, hKey);
    }

    public Long incrementHashValue(final String key, final String hKey, long delta) {
        return redisTemplate.opsForHash().increment(key, hKey, delta);
    }
}

